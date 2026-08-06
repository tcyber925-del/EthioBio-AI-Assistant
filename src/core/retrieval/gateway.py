from __future__ import annotations

import json
from typing import TYPE_CHECKING

import structlog

from src.config import settings
from src.core.retrieval.jina_reranker import JinaReranker
from src.core.retrieval.models import RetrievalResult, TextMatch
from src.core.retrieval.ranking import TrustRanker

if TYPE_CHECKING:
    from src.core.knowledge_registry.service import KnowledgeRegistry
    from src.rag.embedder import Embedder
    from src.rag.vector_store import VectorStore

logger = structlog.get_logger()


class RetrievalGateway:
    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        registry: KnowledgeRegistry,
        ranker: TrustRanker | None = None,
        reranker: JinaReranker | None = None,
    ):
        self._embedder = embedder
        self._vector_store = vector_store
        self._registry = registry
        self._ranker = ranker or TrustRanker()
        self._reranker = reranker
        if self._reranker is None and settings.enable_reranker and settings.jina_api_key:
            self._reranker = JinaReranker()

    async def search(
        self,
        q: str,
        workspace_id: str | None,
        limit: int = 10,
    ) -> list[RetrievalResult]:
        query_embedding = await self._embedder.embed_text(q)
        raw = await self._vector_store.query(
            query_embedding,
            n_results=limit * 3,
        )
        if not raw["documents"]:
            return []

        rerank_scores = None
        if self._reranker is not None:
            try:
                rerank_scores = await self._reranker.rerank(q, raw["documents"])
            except Exception:
                logger.warning("reranker_failed_falling_back", query=q[:50])

        seen: dict[str, dict] = {}
        for i in range(len(raw["documents"])):
            ko_id = raw["metadatas"][i].get("knowledge_object_id", "")
            if rerank_scores is not None and i < len(rerank_scores):
                rs = rerank_scores[i]
                if rs > 0:
                    score = min(1.0, max(0.01, rs))
                else:
                    score = 0.4 * max(0.01, 1.0 - raw["distances"][i])
            else:
                score = 1.0 - raw["distances"][i]
            if ko_id not in seen:
                seen[ko_id] = {"score": score, "chunks": [], "ko_id": ko_id}
            else:
                seen[ko_id]["score"] = max(seen[ko_id]["score"], score)
            seen[ko_id]["chunks"].append(
                TextMatch(
                    text=raw["documents"][i],
                    chunk_index=raw["metadatas"][i].get("chunk_index", 0),
                    score=score,
                )
            )

        results: list[RetrievalResult] = []
        for entry in seen.values():
            ko = await self._registry.get(entry["ko_id"])
            if ko is None:
                continue
            if workspace_id and ko.workspace_id != workspace_id:
                continue
            enrichment_raw = ko.metadata.get("enrichment") if ko.metadata else None
            enrichment = None
            if enrichment_raw:
                try:
                    enrichment = json.loads(enrichment_raw)
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(
                RetrievalResult(
                    ko_id=entry["ko_id"],
                    title=ko.title,
                    content_type=ko.content_type,
                    score=entry["score"],
                    matches=entry["chunks"][:3],
                    workspace_id=ko.workspace_id,
                    enrichment=enrichment,
                )
            )

        results = self._ranker.rerank(results, workspace_id=workspace_id)
        return results[:limit]
