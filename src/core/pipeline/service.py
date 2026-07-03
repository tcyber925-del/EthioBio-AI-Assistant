from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.enrichment.service import EnrichmentService
from src.core.knowledge_registry.models import LifecycleState, LifecycleTransition
from src.core.knowledge_registry.service import KnowledgeRegistry
from src.core.pipeline.models import PipelineResult
from src.core.storage.interface import StorageAdapter
from src.database.models import KnowledgeObject as KnowledgeObjectModel
from src.rag.vector_store import VectorStore

if TYPE_CHECKING:
    from src.rag.embedder import Embedder

logger = structlog.get_logger()


class ValidationError(Exception):
    pass


class PipelineError(Exception):
    pass


def _chunk_text(text: str, ko_id: str, max_chars: int = 1500) -> list[dict]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[dict] = []
    for i, para in enumerate(paragraphs):
        if len(para) <= max_chars:
            chunks.append({"text": para, "heading": "", "page_number": None})
        else:
            sentences = para.replace("\n", " ").split(". ")
            buf = ""
            for sent in sentences:
                candidate = f"{buf}. {sent}".strip() if buf else sent
                if len(candidate) > max_chars and buf:
                    chunks.append({"text": buf + ".", "heading": "", "page_number": None})
                    buf = sent
                else:
                    buf = candidate
            if buf:
                chunks.append({"text": buf, "heading": "", "page_number": None})
    for idx, chunk in enumerate(chunks):
        chunk["id"] = f"{ko_id}:chunk:{idx}"
        chunk["knowledge_object_id"] = ko_id
    return chunks


class PipelineOrchestrator:
    def __init__(
        self,
        registry: KnowledgeRegistry,
        storage: StorageAdapter,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ):
        self._registry = registry
        self._storage = storage
        if embedder is not None:
            self._embedder = embedder
        else:
            from src.rag.embedder import Embedder
            self._embedder = Embedder()
        self._vector_store = vector_store
        self._session_factory = session_factory
        self._enricher = EnrichmentService(registry)

    async def run(
        self,
        ko_id: str,
        file_path: Path,
        max_file_size_mb: int = 50,
    ) -> PipelineResult:
        try:
            await self._run_validation(ko_id, file_path, max_file_size_mb)
            chunks = await self._run_content_extraction_and_chunking(ko_id, file_path)
            if chunks:
                await self._run_embedding_and_indexing(ko_id, chunks)
            await self._run_publication(ko_id)
            await self._run_enrichment(ko_id, chunks)
            logger.info("pipeline_completed", ko_id=ko_id)
            return PipelineResult(ko_id=ko_id, success=True, stage=None)
        except ValidationError as e:
            logger.warning("pipeline_validation_failed", ko_id=ko_id, error=str(e))
            await self._transition_to(ko_id, LifecycleState.FAILED, str(e))
            return PipelineResult(ko_id=ko_id, success=False, stage="validation", error=str(e))
        except Exception as e:
            logger.error("pipeline_failed", ko_id=ko_id, error=str(e))
            await self._transition_to(ko_id, LifecycleState.FAILED, str(e))
            return PipelineResult(ko_id=ko_id, success=False, stage=None, error=str(e))

    async def _run_validation(self, ko_id: str, file_path: Path, max_file_size_mb: int) -> None:
        ext = file_path.suffix.lower()
        if ext not in {".pdf", ".docx", ".txt", ".md"}:
            raise ValidationError(f"Unsupported file format: {ext}")

        size = file_path.stat().st_size
        limit_bytes = max_file_size_mb * 1024 * 1024
        if size > limit_bytes:
            size_mb = size / 1024 / 1024
            raise ValidationError(
                f"File exceeds {max_file_size_mb}MB limit ({size_mb:.1f}MB)"
            )

        content = await _read_file_async(file_path)
        content_hash = hashlib.sha256(content).hexdigest()

        if self._session_factory:
            async with self._session_factory() as db:
                existing = (
                    await db.execute(
                        select(KnowledgeObjectModel).where(
                            KnowledgeObjectModel.content_hash == content_hash,
                            KnowledgeObjectModel.workspace_id.isnot(None),
                            KnowledgeObjectModel.deleted_at.is_(None),
                            KnowledgeObjectModel.lifecycle_state.in_(
                                [
                                    s.value
                                    for s in (
                                        LifecycleState.PUBLISHED,
                                        LifecycleState.ACTIVE,
                                    )
                                ]
                            ),
                        )
                    )
                ).scalars().first()
                if existing is not None:
                    msg = (
                        f"Duplicate content — matches existing KO {existing.id} "
                        f"in workspace {existing.workspace_id}"
                    )
                    raise ValidationError(msg)

        await self._transition_to(ko_id, LifecycleState.PROCESSING, "Validation passed")
        logger.info("validation_passed", ko_id=ko_id, size=size, format=ext)

    async def _run_content_extraction_and_chunking(self, ko_id: str, file_path: Path) -> list[dict]:
        text = await self._extract_text(file_path)
        chunks = _chunk_text(text, ko_id)
        await self._registry.update_metadata(ko_id, {"chunk_count": len(chunks)})
        logger.info("chunking_complete", ko_id=ko_id, chunk_count=len(chunks))
        return chunks

    async def _extract_text(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            return await self._extract_pdf_text(file_path)
        if ext == ".docx":
            return _extract_docx_text(file_path)
        return await _read_text_async(file_path)

    async def _extract_pdf_text(self, file_path: Path) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _extract_pdf_text_sync, file_path)

    async def _run_embedding_and_indexing(self, ko_id: str, chunks: list[dict]) -> None:
        if not self._vector_store:
            logger.warning("no_vector_store_configured, skipping embedding/indexing", ko_id=ko_id)
            return

        texts = [c["text"] for c in chunks]
        chunk_ids = [c["id"] for c in chunks]
        metadatas = [
            {
                "knowledge_object_id": c["knowledge_object_id"],
                "chunk_index": i,
                "heading": c.get("heading", ""),
            }
            for i, c in enumerate(chunks)
        ]

        embeddings = await self._embedder.embed_batch(texts)
        await self._vector_store.add_documents(texts, embeddings, metadatas, chunk_ids)
        logger.info("indexing_complete", ko_id=ko_id, chunk_count=len(chunks))

    async def _run_publication(self, ko_id: str) -> None:
        transition = LifecycleTransition(
            to_state=LifecycleState.PUBLISHED,
            reason="Pipeline completed",
        )
        await self._registry.update_lifecycle(ko_id, transition)
        logger.info("publication_complete", ko_id=ko_id)

    async def _run_enrichment(self, ko_id: str, chunks: list[dict]) -> None:
        if not chunks:
            logger.warning("enrichment_skipped_no_chunks", ko_id=ko_id)
            return
        try:
            ko = await self._registry.get(ko_id)
            content_type = ko.content_type if ko else "text/plain"
            texts = [c["text"] for c in chunks]
            await self._enricher.enrich(ko_id, texts, content_type=content_type)
            logger.info("enrichment_done", ko_id=ko_id)
        except Exception as e:
            logger.warning("enrichment_failed_continuing", ko_id=ko_id, error=str(e))

    async def _transition_to(
        self, ko_id: str, state: LifecycleState, reason: str | None = None
    ) -> None:
        try:
            await self._registry.update_lifecycle(
                ko_id, LifecycleTransition(to_state=state, reason=reason)
            )
        except Exception as e:
            logger.error(
                "lifecycle_transition_failed",
                ko_id=ko_id,
                target=state.value,
                error=str(e),
            )


async def _read_file_async(path: Path) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, path.read_bytes)


async def _read_text_async(path: Path) -> str:
    content = await _read_file_async(path)
    return content.decode("utf-8", errors="replace")


def _extract_pdf_text_sync(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _extract_docx_text(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except ImportError:
        return path.read_text(encoding="utf-8", errors="replace")
