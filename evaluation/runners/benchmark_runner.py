from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from evaluation.datasets.schema import BenchmarkCase
from evaluation.scorers.education import score_weighted_education
from evaluation.scorers.grounding import score_factual_grounding

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkEntryResult:
    id: str
    category: str
    subject: str
    education_scores: dict[str, Any]
    grounding_scores: dict[str, Any]
    weighted_score: float
    passed: bool
    failures: list[str] = field(default_factory=list)


@dataclass
class BenchmarkSuiteResult:
    category: str
    entries: list[BenchmarkEntryResult]
    total: int
    passed: int
    avg_score: float
    avg_education: float
    avg_grounding: float


BENCHMARK_DATASETS: dict[str, str] = {
    "biology": "biology.json",
    "chemistry": "chemistry.json",
    "personalization": "personalization.json",
    "misconceptions": "misconceptions.json",
    "multihop": "multihop.json",
}

BENCHMARK_PASS_THRESHOLD = 0.60


def load_benchmark_dataset(datasets_dir: str, filename: str) -> list[BenchmarkCase]:
    """Load a benchmark dataset file into BenchmarkCase models."""
    filepath = Path(datasets_dir) / filename
    if not filepath.exists():
        logger.warning("Dataset not found: %s", filepath)
        return []

    with open(filepath) as f:
        raw = json.load(f)

    return [BenchmarkCase(**entry) for entry in raw]


def evaluate_benchmark_case(
    case: BenchmarkCase,
    response_text: str | None = None,
) -> BenchmarkEntryResult:
    """Score a single benchmark case using education and grounding scorers.

    If no response_text is provided, uses the case question as a fallback
    (for structural testing of the scorer infrastructure).
    """
    text = response_text or case.question

    edu = score_weighted_education(
        response_text=text,
        expected_topics=case.expected_topics,
        expected_answer_traits=case.expected_answer_traits,
        question=case.question,
        grade_level=case.grade_level,
    )

    grounding = score_factual_grounding(
        response_text=text,
        expected_topics=case.expected_topics,
    )

    failures: list[str] = []
    if edu["weighted_score"] < BENCHMARK_PASS_THRESHOLD:
        failures.append(f"education_score:{edu['weighted_score']:.3f}<threshold:{BENCHMARK_PASS_THRESHOLD:.2f}")
    if grounding["factual_grounding"] < BENCHMARK_PASS_THRESHOLD:
        failures.append(f"grounding:{grounding['factual_grounding']:.3f}<threshold:{BENCHMARK_PASS_THRESHOLD:.2f}")

    return BenchmarkEntryResult(
        id=case.id,
        category=case.category,
        subject=case.subject,
        education_scores=edu,
        grounding_scores=grounding,
        weighted_score=edu["weighted_score"],
        passed=len(failures) == 0,
        failures=failures,
    )


def run_benchmark_suite(
    datasets_dir: str,
    categories: list[str] | None = None,
) -> dict[str, BenchmarkSuiteResult]:
    """Run benchmark suites for specified categories (or all)."""
    if categories is None:
        categories = list(BENCHMARK_DATASETS.keys())

    results: dict[str, BenchmarkSuiteResult] = {}

    for cat in categories:
        filename = BENCHMARK_DATASETS.get(cat)
        if not filename:
            logger.warning("Unknown benchmark category: %s", cat)
            continue

        cases = load_benchmark_dataset(datasets_dir, filename)
        if not cases:
            logger.warning("No cases loaded for %s", cat)
            continue

        entry_results: list[BenchmarkEntryResult] = []
        for case in cases:
            result = evaluate_benchmark_case(case)
            entry_results.append(result)

        total = len(entry_results)
        passed = sum(1 for r in entry_results if r.passed)
        avg_score = (
            sum(r.weighted_score for r in entry_results) / total if total else 0.0
        )
        avg_edu = (
            sum(r.education_scores["weighted_score"] for r in entry_results) / total
            if total
            else 0.0
        )
        avg_ground = (
            sum(r.grounding_scores["factual_grounding"] for r in entry_results) / total
            if total
            else 0.0
        )

        results[cat] = BenchmarkSuiteResult(
            category=cat,
            entries=entry_results,
            total=total,
            passed=passed,
            avg_score=round(avg_score, 3),
            avg_education=round(avg_edu, 3),
            avg_grounding=round(avg_ground, 3),
        )

        logger.info(
            "Benchmark %s: %d/%d passed, avg_score=%.3f, edu=%.3f, ground=%.3f",
            cat,
            passed,
            total,
            avg_score,
            avg_edu,
            avg_ground,
        )

    return results


def write_benchmark_report(
    suite_results: dict[str, BenchmarkSuiteResult],
    report_dir: str = "evaluation/reports",
) -> Path:
    """Write benchmark results to a JSON report file."""
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    serializable: dict[str, Any] = {}
    for cat, result in suite_results.items():
        serializable[cat] = {
            "category": result.category,
            "total": result.total,
            "passed": result.passed,
            "avg_score": result.avg_score,
            "avg_education": result.avg_education,
            "avg_grounding": result.avg_grounding,
            "entries": [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "weighted_score": e.weighted_score,
                    "passed": e.passed,
                    "failures": e.failures,
                    "education_scores": e.education_scores,
                    "grounding_scores": e.grounding_scores,
                }
                for e in result.entries
            ],
        }

    filepath = report_path / "benchmark_report.json"
    with open(filepath, "w") as f:
        json.dump(serializable, f, indent=2)

    logger.info("Benchmark report written to %s", filepath.resolve())
    return filepath
