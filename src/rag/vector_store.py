import os
from typing import Optional

import structlog

from src.config import settings

logger = structlog.get_logger()


class VectorStore:
    def __init__(self, persist_directory: str = None, collection_name: str = None):
        self.persist_directory = persist_directory or settings.vector_store_path
        self.collection_name = collection_name or settings.collection_name
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

    async def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str],
    ):
        collection = self._get_collection()
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info("vectors_added", count=len(texts), collection=self.collection_name)

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        collection = self._get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "ids": results["ids"][0] if results["ids"] else [],
        }

    async def delete_collection(self):
        try:
            client = self._get_client()
            client.delete_collection(self.collection_name)
            self._collection = None
            logger.info("collection_deleted", collection=self.collection_name)
        except Exception as e:
            logger.error("delete_collection_error", error=str(e))

    def count(self) -> int:
        collection = self._get_collection()
        return collection.count()
