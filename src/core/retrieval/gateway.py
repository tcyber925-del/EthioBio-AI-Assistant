from __future__ import annotations

import json
from typing import TYPE_CHECKING

import structlog

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
    ):
        self._embedder = embedder
        self._vector_store = vector_store
        self._registry = registry
        self._ranker = ranker or TrustRanker()

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

        seen: dict[str, dict] = {}
        for i in range(len(raw["documents"])):
            ko_id = raw["metadatas"][i].get("knowledge_object_id", "")
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
