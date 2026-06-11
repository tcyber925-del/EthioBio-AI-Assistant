from __future__ import annotations


def score_query_count(actual_count: int, expected_min: int) -> float:
    """1.0 if actual >= expected_min, else actual/expected_min."""
    if actual_count >= expected_min:
        return 1.0
    if expected_min == 0:
        return 0.0
    return actual_count / expected_min


def score_redundancy(redundant_fraction: float, max_allowed: float) -> float:
    """1.0 if redundancy <= max_allowed, linear decay beyond."""
    if redundant_fraction <= max_allowed:
        return 1.0
    excess = redundant_fraction - max_allowed
    return max(0.0, 1.0 - excess)


def score_source_diversity(
    actual_sources: list[str], expected_diverse: bool
) -> float:
    """1.0 if diversity matches expectation, 0.0 otherwise."""
    unique_sources = len(set(actual_sources))
    is_diverse = unique_sources >= 2
    if expected_diverse:
        return 1.0 if is_diverse else 0.0
    return 1.0
