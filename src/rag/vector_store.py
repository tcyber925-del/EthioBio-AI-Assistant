from typing import Optional

import structlog

from src.config import settings

logger = structlog.get_logger()


class VectorStore:
    def __init__(
        self,
        persist_directory: str = "",
        collection_name: str = "",
    ):
        self.collection_name = collection_name or settings.collection_name
        self._pgvector = self._init_pgvector()

    def _init_pgvector(self):
        from src.rag.pgvector_store import PGVectorStore
        return PGVectorStore(collection_name=self.collection_name)

    @property
    def _use_pgvector(self) -> bool:
        return True

    def _get_pg(self):
        return self._pgvector

    async def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str],
    ):
        return await self._pgvector.add_documents(texts, embeddings, metadatas, ids)

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        return await self._pgvector.query(query_embedding, n_results, where)

    async def delete_collection(self):
        return await self._pgvector.delete_collection()

    async def count(self) -> int:
        return await self._pgvector.count_async()
