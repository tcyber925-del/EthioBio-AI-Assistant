import json
import uuid
from typing import Optional

import structlog
from sqlalchemy import text as sa_text

from src.config import settings
from src.database.models import KnowledgeEmbedding
from src.database.session import async_session_factory

logger = structlog.get_logger()


def _parse_metadata(raw) -> dict:
    if isinstance(raw, dict):
        meta = dict(raw)
    elif isinstance(raw, str):
        if not raw:
            meta = {}
        else:
            try:
                parsed = json.loads(raw)
                meta = parsed if isinstance(parsed, dict) else {}
            except (ValueError, TypeError):
                meta = {}
    else:
        meta = {}
    # Legacy chunks predate the subject field — they are all biology
    meta.setdefault("subject", "biology")
    return meta


class PGVectorStore:
    """PostgreSQL pgvector-backed vector store.

    Implements the same interface as ChromaDB VectorStore so it can be
    swapped transparently. Uses cosine distance (<=>) for similarity search.
    """

    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or settings.collection_name

    async def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str],
    ):
        factory = async_session_factory()
        n = len(texts)
        if not (len(embeddings) == len(metadatas) == len(ids) == n):
            logger.warning(
                "add_documents_length_mismatch",
                texts=len(texts),
                embeddings=len(embeddings),
                metadatas=len(metadatas),
                ids=len(ids),
            )
            n = min(len(texts), len(embeddings), len(metadatas), len(ids))
        async with factory() as session:
            for i in range(n):
                text = texts[i]
                emb = embeddings[i]
                meta = metadatas[i]
                ko_id = meta.get("knowledge_object_id")
                embedding = KnowledgeEmbedding(
                    id=uuid.uuid4(),
                    knowledge_object_id=uuid.UUID(ko_id) if ko_id else None,
                    chunk_index=meta.get("chunk_index", i),
                    content=text,
                    embedding=emb,
                    embedding_metadata={
                        "source_file": meta.get("source_file", ""),
                        "grade_level": meta.get("grade_level", 0),
                        "subject": meta.get("subject", "biology"),
                        "topic": meta.get("topic", ""),
                        "unit": meta.get("unit", ""),
                        "section": meta.get("section", ""),
                        "subtopic": meta.get("subtopic", ""),
                        "source_type": meta.get("source_type", ""),
                        "heading": meta.get("heading", ""),
                        "page_number": meta.get("page_number", 0),
                        "chunk_index": meta.get("chunk_index", i),
                    },
                )
                session.add(embedding)
            await session.commit()
        logger.info("vectors_added_pgvector", count=n)

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        factory = async_session_factory()
        emb_str = f"[{','.join(str(x) for x in query_embedding)}]"

        wheres = ["1=1"]
        params = {"query_vec": emb_str, "limit": n_results}
        if where:
            # to_chroma_where() returns either a single filter dict or
            # {"$and": [filter, ...]} when multiple filters are combined.
            conditions = where.get("$and") if set(where.keys()) == {"$and"} else [where]
            for cond in conditions:
                for key, condition in cond.items():
                    if isinstance(condition, dict) and "$eq" in condition:
                        value = condition["$eq"]
                        if key == "subject":
                            # Legacy chunks lack the subject field — they are all biology
                            wheres.append(
                                "COALESCE(NULLIF(knowledge_embeddings.metadata->>'subject', ''), "
                                "'biology') = :subject"
                            )
                        else:
                            wheres.append(
                                f"COALESCE(knowledge_embeddings.metadata->>'{key}', '') = :{key}"
                            )
                        params[key] = str(value)

        sql = sa_text(
            f"""
            SELECT id, content, metadata, knowledge_object_id,
                   CAST(embedding AS vector({settings.embedding_dimension}))
                       <=> CAST(:query_vec AS vector({settings.embedding_dimension})) AS distance
            FROM knowledge_embeddings
            WHERE {" AND ".join(wheres)}
            ORDER BY distance
            LIMIT :limit
            """
        )

        async with factory() as session:
            result = await session.execute(sql, params)
            rows = result.fetchall()

        metadatas = []
        for r in rows:
            meta = _parse_metadata(r[2])
            if r[3]:
                meta["knowledge_object_id"] = str(r[3])
            metadatas.append(meta)

        return {
            "documents": [r[1] for r in rows],
            "metadatas": metadatas,
            "distances": [float(r[4]) for r in rows],
            "ids": [str(r[0]) for r in rows],
        }

    async def get_all(self) -> dict:
        """Fetch all documents + metadatas + ids (for BM25 index building)."""
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(
                sa_text(
                    "SELECT id, content, metadata FROM knowledge_embeddings ORDER BY created_at"
                )
            )
            rows = result.all()
        documents = [r[1] for r in rows]
        metadatas = [_parse_metadata(r[2]) for r in rows]
        ids = [str(r[0]) for r in rows]
        return {"documents": documents, "metadatas": metadatas, "ids": ids}

    async def delete_collection(self):
        factory = async_session_factory()
        async with factory() as session:
            await session.execute(sa_text("DELETE FROM knowledge_embeddings"))
            await session.commit()
        logger.info("pgvector_collection_cleared")

    async def delete_by_grade(self, grade_level: int) -> int:
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(
                sa_text("DELETE FROM knowledge_embeddings WHERE metadata->>'grade_level' = :grade"),
                {"grade": str(grade_level)},
            )
            await session.commit()
        logger.info("pgvector_grade_cleared", grade_level=grade_level, deleted=result.rowcount)
        return result.rowcount

    async def count_async(self) -> int:
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(sa_text("SELECT COUNT(*) FROM knowledge_embeddings"))
            return result.scalar() or 0

    def count(self) -> int:
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError("count() is sync; use count_async() in async context")
        except RuntimeError:
            pass
        return asyncio.run(self.count_async())

    def _get_collection(self):
        return None
