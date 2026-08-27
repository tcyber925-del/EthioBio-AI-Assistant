from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from src.core.knowledge_registry import KnowledgeRegistry

if TYPE_CHECKING:
    from src.core.event_infrastructure import RedisStreamProducer
from src.core.knowledge_registry.models import (
    KnowledgeFilter,
    KnowledgeObject,
    LifecycleState,
    LifecycleTransition,
    NewKnowledgeObject,
    SearchResult,
)
from src.core.knowledge_registry.models import (
    TextMatch as KOTextMatch,
)
from src.core.pipeline import PipelineOrchestrator
from src.core.pipeline.service import PipelineResult
from src.core.retrieval.gateway import RetrievalGateway
from src.core.storage import StorageAdapter
from src.database.session import async_session_factory
from src.rag.vector_store import VectorStore

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Registry"])

_registry: KnowledgeRegistry | None = None
_producer: RedisStreamProducer | None = None


def _get_registry() -> KnowledgeRegistry:
    global _registry
    if _registry is None:
        _registry = KnowledgeRegistry(async_session_factory())
    return _registry


def _get_producer() -> RedisStreamProducer | None:
    global _producer
    if _producer is None:
        try:
            from src.config import settings
            from src.core.event_infrastructure import RedisStreamProducer

            _producer = RedisStreamProducer(settings.redis_url)
        except Exception:
            logger.warning("redis_producer_unavailable, falling back to inline pipeline")
    return _producer


def _get_storage() -> StorageAdapter:
    from src.core.storage import LocalFileStorage

    return LocalFileStorage()


def _get_pipeline() -> PipelineOrchestrator:
    from src.config import settings
    from src.rag.embedder import Embedder

    return PipelineOrchestrator(
        registry=_get_registry(),
        storage=_get_storage(),
        embedder=Embedder(),
        vector_store=VectorStore(
            persist_directory=settings.vector_store_path,
            collection_name=settings.collection_name,
        ),
        session_factory=async_session_factory(),
    )


async def _run_pipeline_inline(ko_id: str, storage_key: str) -> None:
    try:
        storage = _get_storage()
        file_path = await storage.retrieve(storage_key)
        pipeline = _get_pipeline()
        result: PipelineResult = await pipeline.run(ko_id, file_path)
        if result.success:
            logger.info("pipeline_inline_completed", ko_id=ko_id)
        else:
            logger.warning(
                "pipeline_inline_failed",
                ko_id=ko_id,
                stage=result.stage,
                error=result.error,
            )
    except Exception as e:
        logger.error("pipeline_inline_crashed", ko_id=ko_id, error=str(e))


_gateway: RetrievalGateway | None = None


def _get_gateway() -> RetrievalGateway:
    global _gateway
    if _gateway is None:
        from src.config import settings
        from src.rag.embedder import Embedder

        _gateway = RetrievalGateway(
            embedder=Embedder(),
            vector_store=VectorStore(
                persist_directory=settings.vector_store_path,
                collection_name=settings.collection_name,
            ),
            registry=_get_registry(),
        )
    return _gateway


@router.get("/search", response_model=list[SearchResult])
async def search_knowledge(
    q: str = Query(..., min_length=1),
    workspace_id: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    results = await _get_gateway().search(q=q, workspace_id=workspace_id, limit=limit)
    return [
        SearchResult(
            ko_id=r.ko_id,
            title=r.title,
            content_type=r.content_type,
            score=r.score,
            matches=[
                KOTextMatch(text=m.text, chunk_index=m.chunk_index, score=m.score)
                for m in r.matches
            ],
        )
        for r in results
    ]


@router.post("/upload", status_code=201)
async def upload_knowledge_object(
    file: UploadFile = File(...),
    workspace_id: str = Query(...),
    owner_id: str = Query(...),
    collection_id: str | None = Query(None),
    title: str | None = Query(None),
    content_hash: str | None = Query(None),
    grade_level: int | None = Query(None, ge=1, le=12),
    topic: str | None = Query(None),
    subject: str | None = Query(None),
    unit: str | None = Query(None),
    storage: StorageAdapter = Depends(_get_storage),
):
    upload_title = title or file.filename or "untitled"
    content_type = file.content_type or "application/octet-stream"

    meta: dict = {}
    if grade_level is not None:
        meta["grade_level"] = grade_level
    if topic is not None:
        meta["topic"] = topic
    if subject is not None:
        meta["subject"] = subject
    if unit is not None:
        meta["unit"] = unit

    new_ko = NewKnowledgeObject(
        workspace_id=workspace_id,
        collection_id=collection_id,
        owner_id=owner_id,
        title=upload_title,
        content_type=content_type,
        content_hash=content_hash,
        metadata=meta,
    )

    ko, events = await _get_registry().register(new_ko)

    with NamedTemporaryFile(delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        storage_key = await storage.store(
            tmp_path, workspace_id, ko.id, file.filename or upload_title
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    for event in events:
        logger.info("knowledge_event", event_type=event.event_type, ko_id=ko.id)

    await _get_registry().update_metadata(ko.id, {"storage_key": storage_key})

    producer = _get_producer()
    if producer is not None:
        from src.core.event_infrastructure import PipelineEvent

        pipeline_event = PipelineEvent(
            event_type="knowledge_object_uploaded",
            ko_id=ko.id,
            workspace_id=workspace_id,
            payload={"storage_key": storage_key},
            occurred_at=datetime.now(timezone.utc),
            correlation_id=str(uuid4()),
        )
        try:
            await producer.publish(pipeline_event)
        except Exception:
            logger.warning("redis_publish_failed, falling back to inline pipeline", ko_id=ko.id)
            asyncio.create_task(_run_pipeline_inline(ko.id, storage_key))
    else:
        asyncio.create_task(_run_pipeline_inline(ko.id, storage_key))

    return {
        "id": ko.id,
        "status": "processing",
        "content_type": content_type,
        "storage_key": storage_key,
    }


@router.get("/{ko_id}", response_model=KnowledgeObject)
async def get_knowledge_object(ko_id: str):
    ko = await _get_registry().get(ko_id)
    if ko is None:
        raise HTTPException(status_code=404, detail="KnowledgeObject not found")
    return ko


@router.get("/{ko_id}/download")
async def download_knowledge_object(ko_id: str):
    ko = await _get_registry().get(ko_id)
    if ko is None:
        raise HTTPException(status_code=404, detail="KnowledgeObject not found")

    storage_key = ko.metadata.get("storage_key")
    if not storage_key:
        raise HTTPException(status_code=404, detail="No file stored for this KnowledgeObject")

    from fastapi.responses import FileResponse

    file_path = await _get_storage().retrieve(storage_key)
    return FileResponse(
        path=str(file_path),
        media_type=ko.content_type,
        filename=ko.title,
    )


@router.get("/{ko_id}/enrichment")
async def get_knowledge_enrichment(ko_id: str):
    ko = await _get_registry().get(ko_id)
    if ko is None:
        raise HTTPException(status_code=404, detail="KnowledgeObject not found")

    raw = ko.metadata.get("enrichment")
    if not raw:
        return {"ko_id": ko_id, "enriched": False}

    data = json.loads(raw)
    data["enriched"] = True
    return data


@router.get("/{ko_id}/content")
async def get_knowledge_content(ko_id: str):
    ko = await _get_registry().get(ko_id)
    if ko is None:
        raise HTTPException(status_code=404, detail="KnowledgeObject not found")

    from src.config import settings
    from src.rag.embedder import Embedder

    vector_store = VectorStore(
        persist_directory=settings.vector_store_path,
        collection_name=settings.collection_name,
    )
    dummy_embedding = [0.0] * Embedder().dimension
    raw = await vector_store.query(
        dummy_embedding,
        n_results=1000,
        where={"knowledge_object_id": {"$eq": ko_id}},
    )
    if not raw["documents"]:
        return {"ko_id": ko_id, "content": "", "chunk_count": 0}

    chunks = sorted(
        zip(raw["documents"], raw["metadatas"], strict=False),
        key=lambda x: x[1].get("chunk_index", 0),
    )
    full_text = "\n\n".join(text for text, _ in chunks)
    return {
        "ko_id": ko_id,
        "content": full_text,
        "chunk_count": len(chunks),
    }


@router.get("/", response_model=list[KnowledgeObject])
async def list_knowledge_objects(
    workspace_id: str | None = Query(None),
    collection_id: str | None = Query(None),
    lifecycle_states: str | None = Query(None),
    enrichment_status: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    states = None
    if lifecycle_states:
        states = [LifecycleState(s.strip()) for s in lifecycle_states.split(",")]

    kf = KnowledgeFilter(
        workspace_id=workspace_id,
        collection_id=collection_id,
        lifecycle_states=states,
        enrichment_status=enrichment_status,
        search=search,
        limit=limit,
        offset=offset,
    )
    return await _get_registry().list_by_filter(kf)


@router.patch("/{ko_id}/lifecycle", response_model=KnowledgeObject)
async def update_lifecycle(ko_id: str, transition: LifecycleTransition):
    try:
        ko, _ = await _get_registry().update_lifecycle(ko_id, transition)
        return ko
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{ko_id}/metadata", response_model=KnowledgeObject)
async def update_metadata(ko_id: str, metadata: dict):
    try:
        ko, _ = await _get_registry().update_metadata(ko_id, metadata)
        return ko
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{ko_id}", status_code=204)
async def soft_delete_knowledge_object(ko_id: str):
    try:
        await _get_registry().soft_delete(ko_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{ko_id}/versions")
async def list_versions(ko_id: str):
    return await _get_registry().list_versions(ko_id)


@router.post("/{ko_id}/versions")
async def create_version(ko_id: str):
    try:
        version, _ = await _get_registry().create_version(ko_id)
        return {"ko_id": ko_id, "version": version}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
