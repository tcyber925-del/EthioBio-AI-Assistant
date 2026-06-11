from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


DEFAULT_THRESHOLDS: dict[str, float] = {
    "min_agent_score": 0.70,
    "min_education_score": 0.65,
    "min_factual_grounding": 0.60,
    "min_coverage": 0.50,
    "max_regression_count": 3,
    "min_integration_pass_rate": 0.80,
    "min_certification_score": 0.70,
    "min_production_reliability": 0.80,
    "min_production_security": 0.80,
    "min_production_safety_hardening": 0.80,
    "min_production_governance": 0.80,
    "min_production_cost_efficiency": 0.70,
    "min_production_overall": 0.80,
}

CERTIFICATION_LEVELS = {
    "platinum": 0.90,
    "gold": 0.80,
    "silver": 0.70,
    "bronze": 0.60,
}


@dataclass
class CertificationResult:
    passed: bool
    level: str
    score: float
    checks: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    generated_at: str = ""
    production_ready: bool = False
    production_level: str = ""


@dataclass
class CertificationInput:
    """Aggregated inputs for a release certification decision."""

    agent_scores: dict[str, float]
    education_scores: dict[str, float] | None
    factual_grounding: dict[str, Any] | None
    integration_pass_rate: float | None
    regression_count: int
    benchmark_scores: dict[str, float] | None
    production_scores: dict[str, float] | None = None


def certify_release(
    input_data: CertificationInput,
    thresholds: dict[str, float] | None = None,
) -> CertificationResult:
    """Evaluate whether the system passes release certification.

    Checks all evaluation dimensions against thresholds and
    assigns a certification level (platinum/gold/silver/bronze/fail).
    """
    thresholds = thresholds or DEFAULT_THRESHOLDS
    checks: dict[str, Any] = {}
    failures: list[str] = []

    # 1. Agent scores check
    agent_scores_list = list(input_data.agent_scores.values())
    avg_agent = sum(agent_scores_list) / len(agent_scores_list) if agent_scores_list else 0.0
    min_agent = min(agent_scores_list) if agent_scores_list else 0.0
    checks["avg_agent_score"] = round(avg_agent, 3)
    checks["min_agent_score"] = round(min_agent, 3)
    checks["agent_threshold"] = thresholds["min_agent_score"]
    if min_agent < thresholds["min_agent_score"]:
        failures.append(
            f"agent_score:{min_agent:.3f}<threshold:{thresholds['min_agent_score']:.2f}"
        )

    # 2. Education benchmark scores
    edu_score = 0.0
    if input_data.education_scores:
        edu_values = list(input_data.education_scores.values())
        edu_score = sum(edu_values) / len(edu_values)
        checks["avg_education_score"] = round(edu_score, 3)
        checks["education_threshold"] = thresholds["min_education_score"]
        if edu_score < thresholds["min_education_score"]:
            failures.append(
                f"education_score:{edu_score:.3f}<threshold:{thresholds['min_education_score']:.2f}"
            )

    # 3. Factual grounding
    grounding_score = 0.0
    if input_data.factual_grounding:
        grounding_score = input_data.factual_grounding.get("factual_grounding", 0.0)
        checks["factual_grounding"] = round(grounding_score, 3)
        checks["grounding_threshold"] = thresholds["min_factual_grounding"]
        if grounding_score < thresholds["min_factual_grounding"]:
            failures.append(
                f"grounding:{grounding_score:.3f}<threshold:{thresholds['min_factual_grounding']:.2f}"
            )

    # 4. Integration pass rate
    if input_data.integration_pass_rate is not None:
        checks["integration_pass_rate"] = round(input_data.integration_pass_rate, 3)
        checks["integration_threshold"] = thresholds["min_integration_pass_rate"]
        if input_data.integration_pass_rate < thresholds["min_integration_pass_rate"]:
            failures.append(
                f"integration:{input_data.integration_pass_rate:.3f}<threshold:{thresholds['min_integration_pass_rate']:.2f}"
            )

    # 5. Regression count
    checks["regression_count"] = input_data.regression_count
    checks["regression_threshold"] = thresholds["max_regression_count"]
    if input_data.regression_count > thresholds["max_regression_count"]:
        failures.append(
            f"regressions:{input_data.regression_count}>{thresholds['max_regression_count']}"
        )

    # 6. Benchmark scores
    bench_score = 0.0
    if input_data.benchmark_scores:
        bench_values = list(input_data.benchmark_scores.values())
        bench_score = sum(bench_values) / len(bench_values)
        checks["avg_benchmark_score"] = round(bench_score, 3)

    # 7. Production certification checks (PRD-010D)
    production_ready = False
    production_failures: list[str] = []
    production_level = ""
    if input_data.production_scores:
        production_ready = True
        production_fields = [
            ("reliability", "min_production_reliability"),
            ("security", "min_production_security"),
            ("safety_hardening", "min_production_safety_hardening"),
            ("governance", "min_production_governance"),
            ("cost_efficiency", "min_production_cost_efficiency"),
        ]
        prod_scores_sum = 0.0
        prod_count = 0
        for field_name, threshold_key in production_fields:
            score_val = input_data.production_scores.get(field_name, 0.0)
            thresh = thresholds.get(threshold_key, 0.0)
            checks[f"production_{field_name}"] = round(score_val, 3)
            checks[f"production_{field_name}_threshold"] = thresh
            prod_scores_sum += score_val
            prod_count += 1
            if score_val < thresh:
                production_ready = False
                prod_fail = f"production_{field_name}:{score_val:.3f}<threshold:{thresh:.2f}"
                production_failures.append(prod_fail)
                failures.append(prod_fail)

        prod_overall = prod_scores_sum / prod_count if prod_count > 0 else 0.0
        checks["production_overall"] = round(prod_overall, 3)
        checks["production_overall_threshold"] = thresholds.get("min_production_overall", 0.80)
        if prod_overall < thresholds.get("min_production_overall", 0.80):
            production_ready = False
            thresh = thresholds.get("min_production_overall", 0.80)
            prod_fail = f"production_overall:{prod_overall:.3f}<threshold:{thresh:.2f}"
            production_failures.append(prod_fail)
            failures.append(prod_fail)

        production_levels = {"platinum": 0.95, "gold": 0.90, "silver": 0.80, "bronze": 0.70}
        for lvl, min_s in sorted(production_levels.items(), key=lambda x: -x[1]):
            if prod_overall >= min_s and production_ready:
                production_level = lvl
                break
        if not production_level:
            production_level = "fail"

    # Aggregate score
    weighted_scores = [avg_agent, edu_score, grounding_score]
    valid_scores = [s for s in weighted_scores if s > 0.0]
    aggregate = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0

    checks["aggregate_score"] = round(aggregate, 3)
    checks["certification_threshold"] = thresholds["min_certification_score"]

    if aggregate < thresholds["min_certification_score"]:
        failures.append(
            f"aggregate:{aggregate:.3f}<threshold:{thresholds['min_certification_score']:.2f}"
        )

    passed = len(failures) == 0

    level = "fail"
    for lvl, min_score in sorted(
        CERTIFICATION_LEVELS.items(), key=lambda x: -x[1]
    ):
        if aggregate >= min_score and passed:
            level = lvl
            break

    return CertificationResult(
        passed=passed,
        level=level,
        score=round(aggregate, 3),
        checks=checks,
        failures=failures,
        generated_at=datetime.now().isoformat(),
        production_ready=production_ready,
        production_level=production_level,
    )


def write_certification_report(
    result: CertificationResult,
    report_dir: str = "evaluation/reports",
) -> Path:
    """Write certification result to a JSON report file."""
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    filepath = report_path / "certification_report.json"
    with open(filepath, "w") as f:
        json.dump(asdict(result), f, indent=2)

    logger.info("Certification report written to %s", filepath.resolve())
    return filepath
