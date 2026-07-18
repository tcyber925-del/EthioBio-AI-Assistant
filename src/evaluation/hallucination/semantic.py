import re

from src.evaluation.hallucination.models import (
    ClaimAssessment,
    DetectionMode,
    HallucinationReport,
)

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "can",
    "may",
    "might",
    "shall",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "out",
    "off",
    "over",
    "under",
    "again",
    "further",
    "then",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "each",
    "every",
    "both",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "it",
    "its",
    "this",
    "that",
    "these",
    "those",
}


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _heuristic_support(
    claim_text: str,
    evidence_text: str,
    threshold: float = 0.3,
) -> tuple[bool, float]:
    claim_tokens = _tokenize(claim_text)
    evidence_tokens = _tokenize(evidence_text)
    if not claim_tokens:
        return True, 1.0
    if not evidence_tokens:
        return False, 0.0
    overlap = claim_tokens & evidence_tokens
    ratio = len(overlap) / len(claim_tokens)
    return ratio >= threshold, round(ratio, 3)


async def semantic_check(
    citation_map: list[dict],
    evidence_items: list[dict],
    router=None,
    overlap_threshold: float = 0.3,
) -> HallucinationReport:
    if not citation_map:
        return HallucinationReport(
            supported_claims=0,
            unsupported_claims=0,
            hallucination_rate=0.0,
            grounding_score=1.0,
            claim_assessments=[],
            detection_mode=DetectionMode.SEMANTIC,
        )

    evidence_map = {e["id"]: e for e in evidence_items if "id" in e}
    assessments: list[ClaimAssessment] = []

    for entry in citation_map:
        segment = entry.get("response_segment", "")
        eids = entry.get("evidence_ids", [])

        if router:
            evidence_texts = []
            for eid in eids:
                ev = evidence_map.get(eid, {})
                if ev:
                    evidence_texts.append(ev.get("content", ""))
            combined_evidence = "\n".join(evidence_texts)

            prompt = (
                f"Claim: {segment}\n"
                f"Evidence: {combined_evidence}\n\n"
                "Does the evidence support this claim? "
                "Answer 'supported' or 'unsupported'."
            )
            result = await router.route(
                [{"role": "user", "content": prompt}],
                request_type="hallucination_check",
                temperature=0.1,
                max_tokens=10,
            )
            content = result.get("content", "").strip().lower()
            supported = "supported" in content
            confidence = result.get("confidence", 0.5)
            assessments.append(
                ClaimAssessment(
                    response_segment=segment,
                    evidence_ids=eids,
                    supported=supported,
                    confidence=confidence,
                    reason="llm_assessment" if supported else "llm_flagged",
                )
            )
        else:
            evidence_text = ""
            for eid in eids:
                ev = evidence_map.get(eid, {})
                if ev:
                    evidence_text += " " + ev.get("content", "")
            supported, ratio = _heuristic_support(
                segment,
                evidence_text,
                overlap_threshold,
            )
            assessments.append(
                ClaimAssessment(
                    response_segment=segment,
                    evidence_ids=eids,
                    supported=supported,
                    confidence=ratio,
                    reason="" if supported else "low_token_overlap",
                )
            )

    total = len(assessments)
    supported_count = sum(1 for a in assessments if a.supported)
    unsupported_count = total - supported_count
    h_rate = unsupported_count / total if total > 0 else 0.0

    return HallucinationReport(
        supported_claims=supported_count,
        unsupported_claims=unsupported_count,
        hallucination_rate=h_rate,
        grounding_score=1.0 - h_rate,
        claim_assessments=assessments,
        detection_mode=DetectionMode.SEMANTIC,
    )
