from __future__ import annotations


def score_citation_fidelity(
    response_citations: list[str],
    expected_citations: list[str],
) -> float:
    """Fraction of expected citations present in the response.

    Measures whether the tutor's output cites the correct evidence.
    Expected citations are known-correct evidence IDs or source keys.
    """
    if not expected_citations:
        return 1.0
    expected_set = set(expected_citations)
    if not response_citations:
        return 0.0
    matched = sum(1 for c in response_citations if c in expected_set)
    precision = matched / len(response_citations)
    recall = matched / len(expected_citations)
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * (precision * recall) / (precision + recall)


def score_hallucination_absence(
    hallucinated_claims: int,
    total_claims: int,
    max_rate: float = 0.02,
) -> float:
    """1.0 if hallucination rate <= max_rate, linear decay beyond."""
    if total_claims == 0:
        return 1.0
    rate = hallucinated_claims / total_claims
    if rate <= max_rate:
        return 1.0
    excess = (rate - max_rate) / (1.0 - max_rate)
    return max(0.0, 1.0 - excess)
