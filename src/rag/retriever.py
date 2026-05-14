import structlog
from typing import Optional
from src.rag.embedder import Embedder
from src.rag.vector_store import VectorStore

logger = structlog.get_logger()


class Retriever:
    def __init__(self, embedder: Embedder = None, vector_store: VectorStore = None):
        self.embedder = embedder or Embedder()
        self.vector_store = vector_store or VectorStore()

    async def retrieve(
        self,
        query: str,
        n_results: int = 5,
        grade_level: Optional[int] = None,
        topic: Optional[str] = None,
    ) -> list[dict]:
        query_embedding = await self.embedder.embed_text(query)

        filters = []
        if grade_level:
            filters.append({"grade_level": {"$eq": grade_level}})
        if topic:
            filters.append({"topic": {"$eq": topic}})

        where_clause = None
        if len(filters) == 1:
            where_clause = filters[0]
        elif len(filters) > 1:
            where_clause = {"$and": filters}

        results = await self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where_clause,
        )

        retrieved = []
        for i in range(len(results["documents"])):
            retrieved.append({
                "content": results["documents"][i],
                "metadata": results["metadatas"][i] if i < len(results["metadatas"]) else {},
                "score": 1.0 - results["distances"][i] if i < len(results["distances"]) else 0.0,
                "id": results["ids"][i] if i < len(results["ids"]) else "",
            })

        logger.info("retrieved_documents", count=len(retrieved), query_preview=query[:50])
        return retrieved

    def format_context(self, documents: list[dict]) -> str:
        if not documents:
            return ""

        sections = []
        for i, doc in enumerate(documents, 1):
            topic = doc["metadata"].get("topic", "General")
            grade = doc["metadata"].get("grade_level", "")
            header = f"[Source {i}] Topic: {topic}"
            if grade:
                header += f" | Grade: {grade}"
            sections.append(f"{header}\n{doc['content']}")

        return "\n\n".join(sections)
