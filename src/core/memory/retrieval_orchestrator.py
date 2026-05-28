from datetime import datetime, timezone

import structlog

from src.core.memory.vector_store import MemoryVectorStore
from src.rag.embedder import Embedder

logger = structlog.get_logger()

MEMORY_TOKEN_BUDGET = 1500  # max tokens for memory context
RANK_SIMILARITY_WEIGHT = 0.3
RANK_RECENCY_WEIGHT = 0.4
RANK_CONFIDENCE_WEIGHT = 0.3
RECENCY_HALF_LIFE_DAYS = 14  # recency score halves after this many days


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class MemoryRetrievalResult:
    def __init__(self, memory_id: str, content: str, metadata: dict,
                 score: float, similarity: float):
        self.memory_id = memory_id
        self.content = content
        self.metadata = metadata
        self.score = score
        self.similarity = similarity

    def to_dict(self) -> dict:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "metadata": self.metadata,
            "score": round(self.score, 4),
            "similarity": round(self.similarity, 4),
        }


class RetrievalOrchestrator:
    def __init__(self):
        self.vector_store = MemoryVectorStore()
        self.embedder = Embedder()

    def _recency_score(self, created_at_str: str | None) -> float:
        if not created_at_str:
            return 0.0
        try:
            created = datetime.fromisoformat(created_at_str)
            now = datetime.now(timezone.utc)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age = (now - created).total_seconds() / 86400.0
            return 2.0 ** (-age / RECENCY_HALF_LIFE_DAYS)
        except (ValueError, TypeError):
            return 0.0

    def _combine_scores(self, similarity: float, recency: float,
                        confidence: float) -> float:
        return (
            RANK_SIMILARITY_WEIGHT * similarity
            + RANK_RECENCY_WEIGHT * recency
            + RANK_CONFIDENCE_WEIGHT * confidence
        )

    def _truncate_to_budget(
        self, results: list[MemoryRetrievalResult],
    ) -> list[MemoryRetrievalResult]:
        total_tokens = 0
        truncated = []
        for r in results:
            tokens = estimate_tokens(r.content)
            if total_tokens + tokens > MEMORY_TOKEN_BUDGET:
                remaining = MEMORY_TOKEN_BUDGET - total_tokens
                if remaining > 20:
                    r.content = r.content[:remaining * 4]
                    truncated.append(r)
                break
            total_tokens += tokens
            truncated.append(r)
        logger.info("memory_token_budget", total_tokens=total_tokens,
                    results_returned=len(truncated), budget=MEMORY_TOKEN_BUDGET)
        return truncated

    async def search(
        self,
        query: str,
        n_results: int = 5,
        fetch_size: int = 20,
        topic: str | None = None,
        user_id: str | None = None,
    ) -> list[MemoryRetrievalResult]:
        query_embedding = await self.embedder.embed_text(query)

        where: dict | None = None
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if topic:
            filters["topic"] = topic
        if filters:
            where = {"$and": [{"user_id": v} if k == "user_id" else {k: v}
                              for k, v in filters.items()]}

        raw = await self.vector_store.search(
            query_embedding=query_embedding,
            n_results=fetch_size,
            where=where,
        )

        scored: list[MemoryRetrievalResult] = []
        for item in raw:
            similarity = item.get("score", 0.0)
            meta = item.get("metadata", {})
            confidence = float(meta.get("confidence", 0.0))
            recency = self._recency_score(meta.get("created_at"))
            combined = self._combine_scores(similarity, recency, confidence)

            scored.append(MemoryRetrievalResult(
                memory_id=item.get("id", ""),
                content=item.get("content", ""),
                metadata=meta,
                score=combined,
                similarity=similarity,
            ))

        scored.sort(key=lambda x: x.score, reverse=True)
        truncated = self._truncate_to_budget(scored)
        return truncated[:n_results]

    async def search_by_topic(
        self, topic: str, user_id: str | None = None,
    ) -> list[MemoryRetrievalResult]:
        return await self.search(
            query=f"learning about {topic}",
            n_results=3, fetch_size=10,
            topic=topic, user_id=user_id,
        )
