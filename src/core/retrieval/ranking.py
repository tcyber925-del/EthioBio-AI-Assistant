from __future__ import annotations

from src.core.retrieval.models import RetrievalResult

ENRICHMENT_BONUS = 0.05
WORKSPACE_MATCH_BONUS = 0.02
LESSON_REFERENCE_BONUS = 0.03


class TrustRanker:
    def rerank(
        self,
        results: list[RetrievalResult],
        workspace_id: str | None = None,
    ) -> list[RetrievalResult]:
        scored = [(self._score_with_boosts(r, workspace_id), r) for r in results]
        scored.sort(key=lambda x: -x[0])
        for s, r in scored:
            r.score = s
        return [r for _, r in scored]

    def _score_with_boosts(
        self, result: RetrievalResult, workspace_id: str | None
    ) -> float:
        score = result.score
        if result.enrichment:
            score += ENRICHMENT_BONUS
            content_class = result.enrichment.get("content_class")
            if content_class in ("lesson", "reference"):
                score += LESSON_REFERENCE_BONUS
        if workspace_id and result.workspace_id == workspace_id:
            score += WORKSPACE_MATCH_BONUS
        return score
