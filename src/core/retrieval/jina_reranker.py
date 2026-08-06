"""Hosted cross-encoder reranking via Jina AI /v1/rerank.

Free tier: 10M tokens per API key (100 RPM). Never crashes retrieval —
callers catch :class:`RerankerError` and fall back.
"""
from __future__ import annotations

import httpx
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


class RerankerError(Exception):
    pass


class JinaReranker:
    def __init__(self) -> None:
        self.model = settings.jina_reranker_model
        self.base_url = settings.jina_reranker_base_url
        self.api_key = settings.jina_api_key
        self.batch_size = settings.reranker_batch_size

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        scores = [0.0] * len(documents)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        for idx in range(0, len(documents), self.batch_size):
            batch = documents[idx : idx + self.batch_size]
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                    resp = await client.post(
                        f"{self.base_url}/rerank",
                        headers=headers,
                        json={
                            "model": self.model,
                            "query": query,
                            "documents": batch,
                            "top_n": len(batch),
                        },
                    )
                if resp.status_code != 200:
                    raise RerankerError(f"jina rerank HTTP {resp.status_code}")
                results = resp.json().get("results", [])
                for item in results:
                    index = item.get("index")
                    if index is not None and idx + index < len(scores):
                        scores[idx + index] = float(item.get("relevance_score") or 0.0)
            except httpx.HTTPError as e:
                raise RerankerError(f"jina rerank request failed: {e}") from e
        return scores
