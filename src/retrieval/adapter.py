"""
VectorStoreAdapter — abstraction layer over ChromaDB.

All retrieval-adjacent code goes through this interface.
ChromaDB can be swapped without touching agents or ingestion.
"""

from typing import Optional
from src.rag.embedder import Embedder
from src.rag.vector_store import VectorStore
import structlog

logger = structlog.get_logger()


class RetrievalResult:
    def __init__(self, content: str, metadata: dict, score: float, source_id: str):
        self.content = content
        self.metadata = metadata
        self.score = score
        self.source_id = source_id


class RetrievalFilter:
    def __init__(
        self,
        grade_level: Optional[int] = None,
        topic: Optional[str] = None,
        unit: Optional[str] = None,
        source_type: Optional[str] = None,
        language: str = "en",
    ):
        self.grade_level = grade_level
        self.topic = topic
        self.unit = unit
        self.source_type = source_type
        self.language = language

    def to_chroma_where(self) -> Optional[dict]:
        filters = []
        if self.grade_level:
            filters.append({"grade_level": {"$eq": self.grade_level}})
        if self.topic:
            filters.append({"topic": {"$eq": self.topic}})
        if self.unit:
            filters.append({"unit": {"$eq": self.unit}})
        if self.source_type:
            filters.append({"source_type": {"$eq": self.source_type}})

        if not filters:
            return None
        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}


class VectorStoreAdapter:
    def __init__(self, embedder: Optional[Embedder] = None, vector_store: Optional[VectorStore] = None):
        self.embedder = embedder or Embedder()
        self.vector_store = vector_store or VectorStore()

    async def search(
        self,
        query: str,
        n_results: int = 5,
        filter_obj: Optional[RetrievalFilter] = None,
    ) -> list[RetrievalResult]:
        query_embedding = await self.embedder.embed_text(query)
        where = filter_obj.to_chroma_where() if filter_obj else None

        results = await self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )

        retrieved = []
        for i in range(len(results["documents"])):
            retrieved.append(RetrievalResult(
                content=results["documents"][i],
                metadata=results["metadatas"][i] if i < len(results["metadatas"]) else {},
                score=1.0 - results["distances"][i] if i < len(results["distances"]) else 0.0,
                source_id=results["ids"][i] if i < len(results["ids"]) else "",
            ))

        logger.info("adapter_search", query_preview=query[:50], results=len(retrieved))
        return retrieved

    def format_context(self, results: list[RetrievalResult], max_chars: int = 4000) -> str:
        sections = []
        char_count = 0
        for i, r in enumerate(results, 1):
            header = ""
            grade = r.metadata.get("grade_level", "")
            topic = r.metadata.get("topic", "") or r.metadata.get("heading", "")
            if grade:
                header = f"[Source {i}] Grade {grade}"
                if topic:
                    header += f" | {topic}"
            else:
                header = f"[Source {i}]"
            if r.metadata.get("source_type"):
                header += f" ({r.metadata['source_type']})"

            entry = f"{header}\n{r.content}"
            if char_count + len(entry) > max_chars:
                remaining = max_chars - char_count
                if remaining > 200:
                    sections.append(f"{header}\n{r.content[:remaining]}...")
                break

            sections.append(entry)
            char_count += len(entry)

        return "\n\n".join(sections)

    def count(self) -> int:
        return self.vector_store.count()
