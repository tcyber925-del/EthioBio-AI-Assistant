import uuid
from typing import Optional

import structlog
from sqlalchemy import text as sa_text

from src.config import settings
from src.database.models import KnowledgeEmbedding
from src.database.session import async_session_factory

logger = structlog.get_logger()


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
        async with factory() as session:
            for i, (text, emb, meta, _doc_id) in enumerate(zip(texts, embeddings, metadatas, ids)):
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
        logger.info("vectors_added_pgvector", count=len(texts))

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
            for key, condition in where.items():
                if isinstance(condition, dict) and "$eq" in condition:
                    wheres.append(
                        f"COALESCE(knowledge_embeddings.metadata->>'{key}', '') = :{key}"
                    )
                    params[key] = str(condition["$eq"])

        sql = sa_text(
            f"""
            SELECT id, content, metadata,
                   CAST(embedding AS vector({settings.embedding_dimension}))
                       <=> CAST(:query_vec AS vector({settings.embedding_dimension})) AS distance
            FROM knowledge_embeddings
            WHERE {' AND '.join(wheres)}
            ORDER BY distance
            LIMIT :limit
            """
        )

        async with factory() as session:
            result = await session.execute(sql, params)
            rows = result.fetchall()

        return {
            "documents": [r[1] for r in rows],
            "metadatas": [r[2] if isinstance(r[2], dict) else {} for r in rows],
            "distances": [float(r[3]) for r in rows],
            "ids": [str(r[0]) for r in rows],
        }

    async def get_all(self) -> dict:
        """Fetch all documents + metadatas + ids (for BM25 index building)."""
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(
                sa_text(
                    "SELECT id, content, metadata "
                    "FROM knowledge_embeddings ORDER BY created_at"
                )
            )
            rows = result.all()
        documents = [r[1] for r in rows]
        metadatas = [r[2] for r in rows]
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
                sa_text(
                    "DELETE FROM knowledge_embeddings "
                    "WHERE metadata->>'grade_level' = :grade"
                ),
                {"grade": str(grade_level)},
            )
            await session.commit()
        logger.info("pgvector_grade_cleared", grade_level=grade_level, deleted=result.rowcount)
        return result.rowcount

    async def count_async(self) -> int:
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(
                sa_text("SELECT COUNT(*) FROM knowledge_embeddings")
            )
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
