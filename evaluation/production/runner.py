from __future__ import annotations

from typing import Any

from evaluation.production.cost_efficiency import run_cost_efficiency_checks
from evaluation.production.governance import run_governance_checks
from evaluation.production.reliability import run_reliability_checks
from evaluation.production.safety_hardening import run_safety_hardening_checks
from evaluation.production.security import run_security_checks

PRODUCTION_CATEGORIES = [
    "reliability",
    "security",
    "safety_hardening",
    "governance",
    "cost_efficiency",
]

PRODUCTION_RUNNERS = {
    "reliability": run_reliability_checks,
    "security": run_security_checks,
    "safety_hardening": run_safety_hardening_checks,
    "governance": run_governance_checks,
    "cost_efficiency": run_cost_efficiency_checks,
}

PRODUCTION_THRESHOLDS: dict[str, float] = {
    "reliability": 0.80,
    "security": 0.80,
    "safety_hardening": 0.80,
    "governance": 0.80,
    "cost_efficiency": 0.70,
}


def run_all_production_checks(
    categories: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Run all (or specified) production certification checks."""
    if categories is None:
        categories = list(PRODUCTION_CATEGORIES)

    results: dict[str, dict[str, Any]] = {}
    for cat in categories:
        runner = PRODUCTION_RUNNERS.get(cat)
        if runner is None:
            continue
        results[cat] = runner()
    return results


def get_production_scores(
    results: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """Extract scores from production check results."""
    return {cat: info["score"] for cat, info in results.items()}


def check_production_thresholds(
    results: dict[str, dict[str, Any]],
    thresholds: dict[str, float] | None = None,
) -> list[str]:
    """Check which production categories fail their thresholds."""
    if thresholds is None:
        thresholds = PRODUCTION_THRESHOLDS

    failures: list[str] = []
    for cat, info in results.items():
        threshold = thresholds.get(cat, 0.0)
        if info["score"] < threshold:
            failures.append(f"{cat}:{info['score']:.3f}<threshold:{threshold:.2f}")
    return failures
