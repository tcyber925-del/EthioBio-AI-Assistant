"""Evidence Selector component for Agentic RAG.

Selects top evidence bundle for generation using weighted scoring.
Heuristic for MVP with LLM-based fallback for tie-breaking.
"""

import logging
from dataclasses import dataclass

from src.core.evidence.scoring import SOURCE_QUALITY, calculate_confidence

logger = logging.getLogger(__name__)

# Selection constants
MAX_EVIDENCE_RECORDS = 10
MIN_EVIDENCE_RECORDS = 2
DIVERSITY_PENALTY = 0.15  # penalty per duplicate source
RECENCY_BOOST = 0.05  # bonus per index position (earlier = more recent)

# Selection weights
SELECTION_WEIGHTS = {
    "confidence": 0.35,
    "coverage": 0.25,
    "source_quality": 0.20,
    "diversity": 0.15,
    "recency": 0.05,
}

LLM_FALLBACK_PROMPT = """You are a evidence selector.

Rank these evidence items by relevance and select the top {max_records} for answering:

Question: {question}

Evidence items:
{evidence_items}

Return ONLY a JSON list of indices in rank order: [2, 0, 3, ...]"""


@dataclass
class ScoredEvidence:
    """Evidence with selection score."""

    index: int
    evidence_id: str
    content: str
    source_type: str
    source_name: str
    retrieval_score: float
    rerank_score: float
    confidence: float
    selection_score: float


def score_evidence(
    item: dict,
    index: int,
    question_words: set[str],
    already_selected_sources: set[str],
) -> float:
    """Calculate weighted selection score for an evidence item.

    Combines 5 criteria:
    1. Confidence (35%) — retrieval + rerank scores
    2. Coverage (25%) — does it cover question terms?
    3. Source quality (20%) — curriculum vs. memory vs. misconceptions
    4. Diversity (15%) — penalty for duplicate sources
    5. Recency (5%) — small boost for earlier items

    Args:
        item: Evidence dict with content, score, source fields.
        index: Position in original list.
        question_words: Set of significant question terms.
        already_selected_sources: Set of sources already in bundle.

    Returns:
        Normalized selection score (0.0-1.0).
    """
    retrieval_score = item.get("score", item.get("retrieval_score", 0.5))
    rerank_score = item.get("rerank_score", retrieval_score)
    source_type = item.get("source", item.get("source_type", "unknown"))
    content = item.get("content", "")

    # 1. Confidence score (35%)
    conf = calculate_confidence(retrieval_score, rerank_score, source_type)
    confidence_score = conf.final_score

    # 2. Coverage score (25%)
    content_lower = content.lower()
    covered_words = sum(1 for w in question_words if w in content_lower)
    coverage_score = covered_words / max(len(question_words), 1)

    # 3. Source quality (20%)
    source_quality = SOURCE_QUALITY.get(source_type, 0.5)

    # 4. Diversity (15%)
    diversity_score = 1.0
    if item.get("source_name", "") in already_selected_sources:
        diversity_score = 1.0 - DIVERSITY_PENALTY

    # 5. Recency (5%)
    recency_score = min(1.0, index * RECENCY_BOOST)

    # Weighted total
    total = (
        confidence_score * SELECTION_WEIGHTS["confidence"]
        + coverage_score * SELECTION_WEIGHTS["coverage"]
        + source_quality * SELECTION_WEIGHTS["source_quality"]
        + diversity_score * SELECTION_WEIGHTS["diversity"]
        + recency_score * SELECTION_WEIGHTS["recency"]
    )

    return min(1.0, max(0.0, total))


def greedy_select(
    scored: list[ScoredEvidence], max_records: int
) -> list[ScoredEvidence]:
    """Greedy selection with diversity constraint.

    Picks highest-scored item first, then penalizes subsequent items
    from the same source. Ensures diverse coverage.

    Args:
        scored: List of ScoredEvidence items.
        max_records: Maximum number to select.

    Returns:
        Selected items in priority order.
    """
    if not scored:
        return []

    selected: list[ScoredEvidence] = []
    selected_sources: set[str] = set()
    remaining = list(scored)

    while remaining and len(selected) < max_records:
        # Re-score remaining items with diversity penalty
        for item in remaining:
            if item.source_name in selected_sources:
                item.selection_score *= 1.0 - DIVERSITY_PENALTY

        # Sort by score descending
        remaining.sort(key=lambda x: x.selection_score, reverse=True)

        # Pick the best
        best = remaining.pop(0)
        selected.append(best)
        selected_sources.add(best.source_name)

    return selected


class EvidenceSelector:
    """Selects the top evidence bundle for generation.

    Ranks evidence by coverage contribution, confidence, source quality,
    relevance, and diversity. Caps at ~8-10 records per generation.

    Phase 0: Heuristic selection (deterministic, zero latency).
    Phase 1+: LLM-based fallback for tie-breaking.
    """

    def __init__(self, graph=None, router=None):
        """Initialize with optional EvidenceGraph and LLM router.

        Args:
            graph: Optional EvidenceGraph instance for lookup.
            router: Optional ModelRouter for LLM fallback.
        """
        self.graph = graph
        self.router = router

    async def select_for_generation(
        self,
        evidence_ids: list[str],
        max_tokens: int = 4096,
        question: str = "",
    ) -> list[str]:
        """Select top evidence for generation.

        Uses heuristic weighted scoring with greedy diversity selection.
        Falls back to LLM ranking when heuristic is ambiguous (ties).

        Args:
            evidence_ids: List of evidence IDs to choose from.
            max_tokens: Token budget for evidence (not yet used).
            question: Original question for coverage analysis.

        Returns:
            Selected evidence IDs in priority order.
        """
        if not evidence_ids:
            return []

        # If we have a graph, resolve IDs to full evidence items
        if self.graph:
            evidence_items = []
            for eid in evidence_ids:
                evidence = await self.graph.get(eid)
                if evidence:
                    evidence_items.append({
                        "id": str(evidence.id),
                        "content": evidence.content,
                        "source": evidence.source_type,
                        "source_type": evidence.source_type,
                        "source_name": evidence.source_name,
                        "score": evidence.confidence,
                        "retrieval_score": evidence.retrieval_score,
                        "rerank_score": evidence.rerank_score,
                    })
        else:
            # Without a graph, use IDs as-is (passthrough mode)
            return evidence_ids[:MAX_EVIDENCE_RECORDS]

        if len(evidence_items) <= MIN_EVIDENCE_RECORDS:
            return [item["id"] for item in evidence_items]

        # Question words for coverage scoring
        question_words = {
            w.lower() for w in question.split() if len(w) > 3
        } if question else set()

        # Score each evidence item
        scored: list[ScoredEvidence] = []
        for i, item in enumerate(evidence_items):
            score = score_evidence(
                item=item,
                index=i,
                question_words=question_words,
                already_selected_sources=set(),
            )
            scored.append(ScoredEvidence(
                index=i,
                evidence_id=item["id"],
                content=item.get("content", ""),
                source_type=item.get("source_type", "unknown"),
                source_name=item.get("source_name", item.get("source", "unknown")),
                retrieval_score=item.get("retrieval_score", 0.5),
                rerank_score=item.get("rerank_score", 0.5),
                confidence=item.get("confidence", item.get("score", 0.5)),
                selection_score=score,
            ))

        # Heuristic: greedy selection with diversity
        selected = greedy_select(scored, MAX_EVIDENCE_RECORDS)

        # LLM fallback: use when top scores are very close (within 5%)
        if self.router and len(selected) >= 2:
            top_two_diff = abs(selected[0].selection_score - selected[1].selection_score)
            if top_two_diff < 0.05:
                llm_result = await self._rank_with_llm(
                    selected[:5], question
                )
                if llm_result:
                    return llm_result

        return [s.evidence_id for s in selected]

    async def _rank_with_llm(
        self, candidates: list[ScoredEvidence], question: str
    ) -> list[str] | None:
        """Use LLM to break ties in evidence ranking.

        Args:
            candidates: Short list of top candidates.
            question: Original question for context.

        Returns:
            Re-ranked evidence IDs, or None if LLM fails.
        """
        if not self.router or not candidates:
            return None

        evidence_lines = []
        for i, c in enumerate(candidates):
            evidence_lines.append(
                f"[{i}] (score={c.selection_score:.2f}, "
                f"source={c.source_type}/{c.source_name}) "
                f"{c.content[:150]}..."
            )

        prompt = LLM_FALLBACK_PROMPT.format(
            question=question or "unknown",
            max_records=len(candidates),
            evidence_items="\n".join(evidence_lines),
        )

        try:
            response = await self.router.generate(
                system="You are a precise evidence ranker. Return only a JSON array of indices.",
                user=prompt,
            )
            import json

            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response

            indices = json.loads(json_str)
            return [candidates[i].evidence_id for i in indices if i < len(candidates)]

        except Exception as e:
            logger.warning("llm_ranking_failed: %s", str(e))
            return None
