import os

import structlog

from src.config import settings

logger = structlog.get_logger()

MEMORY_COLLECTION_NAME = "educational_memories"


class MemoryVectorStore:
    def __init__(self, persist_directory: str | None = None):
        self.persist_directory = persist_directory or settings.vector_store_path
        self.collection_name = MEMORY_COLLECTION_NAME
        self._client = None
        self._collection = None

    def _get_client(self):
        if self._client is None:
            import chromadb
            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
        return self._client

    def _get_collection(self):
        if self._collection is None:
            client = self._get_client()
            try:
                self._collection = client.get_collection(self.collection_name)
            except Exception:
                self._collection = client.create_collection(self.collection_name)
        return self._collection

    async def add_memory(
        self, embedding: list[float], text: str,
        metadata: dict, memory_id: str,
    ):
        collection = self._get_collection()
        collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
            ids=[memory_id],
        )
        logger.info("memory_vector_added", memory_id=memory_id)

    async def search(
        self, query_embedding: list[float],
        n_results: int = 5, where: dict | None = None,
    ) -> list[dict]:
        collection = self._get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )
        retrieved = []
        if results["documents"]:
            for i in range(len(results["documents"][0])):
                retrieved.append({
                    "id": results["ids"][0][i] if results["ids"] else "",
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1.0 - results["distances"][0][i]
                    if results["distances"] else 0.0,
                })
        return retrieved

    async def delete_memory(self, memory_id: str):
        try:
            collection = self._get_collection()
            collection.delete(ids=[memory_id])
        except Exception as e:
            logger.warning("memory_vector_delete_error", memory_id=memory_id, error=str(e))

    def count(self) -> int:
        collection = self._get_collection()
        return collection.count()
