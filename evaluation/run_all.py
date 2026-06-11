#!/usr/bin/env python3
"""CLI entry point for the Agent & Integration Evaluation Framework.

Usage:
    python evaluation/run_all.py --all
    python evaluation/run_all.py --planner --rewriter
    python evaluation/run_all.py --integration
    python evaluation/run_all.py --contracts --journeys
    python evaluation/run_all.py --benchmarks
    python evaluation/run_all.py --biology --chemistry
    python evaluation/run_all.py --production
    python evaluation/run_all.py --certify
    python evaluation/run_all.py --all --save-baseline
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path

from evaluation.models import ComponentType

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

INTEGRATION_MARKERS = {
    "contracts": "tests/contracts/",
    "journeys": "tests/journeys/",
    "workflows": "tests/workflows/",
    "integration": "tests/integration/",
}

BENCHMARK_CATEGORIES = [
    "biology",
    "chemistry",
    "personalization",
    "misconceptions",
    "multihop",
]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Agent & Integration Evaluation Framework CLI"
    )
    # Agent evaluation flags (PRD-010A)
    parser.add_argument("--all", action="store_true", help="Run all evaluations")
    parser.add_argument("--planner", action="store_true", help="Evaluate Planner Agent")
    parser.add_argument("--rewriter", action="store_true", help="Evaluate Query Rewriter")
    parser.add_argument("--fanout", action="store_true", help="Evaluate Search Fanout")
    parser.add_argument("--evidence", action="store_true", help="Evaluate Evidence Graph")
    parser.add_argument("--context", action="store_true", help="Evaluate Sufficient Context")
    parser.add_argument("--loop", action="store_true", help="Evaluate Retrieval Loop")
    parser.add_argument("--tutor", action="store_true", help="Evaluate Tutor Agent")
    # Integration test flags (PRD-010B)
    parser.add_argument("--integration", action="store_true", help="Run all integration tests")
    parser.add_argument("--contracts", action="store_true", help="Run contract tests")
    parser.add_argument("--journeys", action="store_true", help="Run journey tests")
    parser.add_argument("--workflows", action="store_true", help="Run workflow tests")
    # Benchmark flags (PRD-010C)
    parser.add_argument("--benchmarks", action="store_true", help="Run all educational benchmarks")
    for cat in BENCHMARK_CATEGORIES:
        parser.add_argument(f"--{cat}", action="store_true", help=f"Run {cat} benchmarks")
    # Certification flag (PRD-010C)
    parser.add_argument("--certify", action="store_true", help="Run release certification check")
    # Production readiness flags (PRD-010D)
    parser.add_argument("--production", action="store_true", help="Run all production readiness checks")
    # Shared
    parser.add_argument(
        "--report-dir",
        default="evaluation/reports",
        help="Directory to write report JSON files",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save scores as new regression baseline",
    )
    parser.add_argument("--mock", action="store_true", default=True, help="Use mock LLM")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    has_agent_flags = any([
        args.planner, args.rewriter, args.fanout, args.evidence,
        args.context, args.loop, args.tutor,
    ])
    has_integration_flags = any([
        args.contracts, args.journeys, args.workflows, args.integration,
    ])
    has_benchmark_flags = any([
        args.benchmarks,
        *[getattr(args, cat, False) for cat in BENCHMARK_CATEGORIES],
    ])
    has_production_flags = args.production
    has_any_flag = has_agent_flags or has_integration_flags or has_benchmark_flags or has_production_flags or args.certify

    if not has_any_flag:
        args.all = True

    return args


def _resolve_components(args: argparse.Namespace) -> list[ComponentType]:
    if args.all and not any([
        args.contracts, args.journeys, args.workflows, args.integration,
    ]):
        return list(ComponentType)
    components: list[ComponentType] = []
    mapping = {
        "planner": ComponentType.PLANNER,
        "rewriter": ComponentType.QUERY_REWRITER,
        "fanout": ComponentType.SEARCH_FANOUT,
        "evidence": ComponentType.EVIDENCE_GRAPH,
        "context": ComponentType.SUFFICIENT_CONTEXT,
        "loop": ComponentType.RETRIEVAL_LOOP,
        "tutor": ComponentType.TUTOR,
    }
    for flag, ct in mapping.items():
        if getattr(args, flag, False):
            components.append(ct)
    return components


def _resolve_benchmark_categories(args: argparse.Namespace) -> list[str]:
    if args.all or args.benchmarks:
        return list(BENCHMARK_CATEGORIES)
    return [cat for cat in BENCHMARK_CATEGORIES if getattr(args, cat, False)]


def _run_integration_pytest(target_dir: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", target_dir, "-v", "--tb=short"],
        capture_output=True, text=True, timeout=120,
    )
    return {
        "passed": "passed" in result.stderr or "passed" in result.stdout,
        "exit_code": result.returncode,
        "output": result.stdout + result.stderr,
    }


def _write_reports(summary, report_dir: str) -> None:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    summary_path = report_path / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary.model_dump(), f, indent=2)

    for result in summary.results:
        component_path = report_path / f"{result.component.value}.json"
        with open(component_path, "w") as f:
            json.dump(result.model_dump(), f, indent=2)

    logger.info("Reports written to %s", report_path.resolve())


def _save_baseline(summary, regression_dir: str) -> None:
    baseline_path = Path(regression_dir) / "baseline_scores.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)

    baseline = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "components": {
            ct: {"score": score}
            for ct, score in summary.component_scores.items()
        },
    }
    with open(baseline_path, "w") as f:
        json.dump(baseline, f, indent=2)

    logger.info("Baseline saved to %s", baseline_path.resolve())


def _write_integration_report(results: dict, report_dir: str) -> None:
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    integration_path = report_path / "integration_summary.json"
    with open(integration_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Integration report written to %s", integration_path.resolve())


async def run_agent_evaluation(args: argparse.Namespace) -> int:
    """Run agent-level evaluations (PRD-010A)."""
    components = _resolve_components(args)
    if not components:
        return 0

    from evaluation.runners.runner import EvalRunner

    runner = EvalRunner(
        datasets_dir="evaluation/datasets",
        mock_llm="mock" if args.mock else None,
    )

    summary = await runner.evaluate_all(filters=components)
    _write_reports(summary, args.report_dir)

    if args.save_baseline:
        _save_baseline(summary, "evaluation/regression")

    logger.info(
        "Agent Score: %s | Passed: %d/%d | Regressions: %d",
        summary.aggregate_score,
        summary.passed,
        summary.total_components,
        len(summary.regressions),
    )
    return 0 if summary.failed == 0 else 1


def run_integration_tests(args: argparse.Namespace) -> int:
    """Run integration-level tests (PRD-010B)."""
    markers_to_run = []
    if args.all or args.integration:
        markers_to_run = list(INTEGRATION_MARKERS.values())
    else:
        for name, path in INTEGRATION_MARKERS.items():
            if getattr(args, name, False):
                markers_to_run.append(path)

    if not markers_to_run:
        return 0

    results = {}
    all_passed = True
    for target in markers_to_run:
        rel_path = Path(target)
        if not rel_path.exists():
            logger.warning("Integration target not found: %s", target)
            continue
        result = _run_integration_pytest(target)
        results[target] = result
        passed = result["exit_code"] == 0
        if not passed:
            all_passed = False
            logger.error("Integration tests failed: %s", target)
            logger.error(result["output"][:2000])
        else:
            logger.info("Integration tests passed: %s", target)

    _write_integration_report(results, args.report_dir)

    for target, result in results.items():
        name = target.replace("tests/", "").replace("/", "")
        result_path = Path(args.report_dir) / f"{name}_results.json"
        with open(result_path, "w") as f:
            json.dump(result, f, indent=2)

    return 0 if all_passed else 1


def run_benchmarks(args: argparse.Namespace) -> int:
    """Run educational benchmarks (PRD-010C)."""
    categories = _resolve_benchmark_categories(args)
    if not categories:
        return 0

    from evaluation.runners.benchmark_runner import (
        run_benchmark_suite,
        write_benchmark_report,
    )

    suite_results = run_benchmark_suite(
        datasets_dir="evaluation/datasets",
        categories=categories,
    )
    write_benchmark_report(suite_results, args.report_dir)

    overall_passed = all(r.passed == r.total for r in suite_results.values())
    for cat, result in suite_results.items():
        logger.info(
            "%s: %d/%d passed (%.3f)",
            cat, result.passed, result.total, result.avg_score,
        )

    return 0 if overall_passed else 1


def run_certification(args: argparse.Namespace) -> int:
    """Run release certification check (PRD-010C)."""
    from evaluation.certification.certifier import (
        CertificationInput,
        certify_release,
        write_certification_report,
    )
    from evaluation.runners.benchmark_runner import (
        run_benchmark_suite,
    )

    suite_results = run_benchmark_suite(datasets_dir="evaluation/datasets")

    benchmark_scores: dict[str, float] = {}
    for cat, suite_result in suite_results.items():
        benchmark_scores[cat] = suite_result.avg_score

    input_data = CertificationInput(
        agent_scores={},
        education_scores=benchmark_scores,
        factual_grounding={"factual_grounding": 0.0},
        integration_pass_rate=None,
        regression_count=0,
        benchmark_scores=benchmark_scores,
    )

    cert_result = certify_release(input_data)
    write_certification_report(cert_result, args.report_dir)

    if cert_result.passed:
        logger.info(
            "Certification: %s (level=%s, score=%.3f)",
            "PASSED", cert_result.level, cert_result.score,
        )
    else:
        logger.error(
            "Certification: FAILED (score=%.3f, failures=%s)",
            cert_result.score, cert_result.failures,
        )

    return 0 if cert_result.passed else 1


def run_production_checks(args: argparse.Namespace) -> int:
    """Run production readiness checks (PRD-010D)."""
    from evaluation.production.runner import (
        PRODUCTION_THRESHOLDS,
        check_production_thresholds,
        get_production_scores,
        run_all_production_checks,
    )

    results = run_all_production_checks()
    scores = get_production_scores(results)
    threshold_failures = check_production_thresholds(results, PRODUCTION_THRESHOLDS)

    for cat, info in sorted(results.items()):
        status = "PASS" if info["passed"] == info["total"] else "FAIL"
        logger.info("[%s] %s: %d/%d (score=%.3f)", status, cat, info["passed"], info["total"], info["score"])

    if threshold_failures:
        for f in threshold_failures:
            logger.error("Production threshold failure: %s", f)

    return 0 if len(threshold_failures) == 0 else 1


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    agent_exit = await run_agent_evaluation(args)
    integration_exit = run_integration_tests(args)

    if args.all or args.benchmarks or any(
        getattr(args, cat, False) for cat in BENCHMARK_CATEGORIES
    ):
        benchmark_exit = run_benchmarks(args)
    else:
        benchmark_exit = 0

    if args.all or args.certify:
        certify_exit = run_certification(args)
    else:
        certify_exit = 0

    if args.all or args.production:
        production_exit = run_production_checks(args)
    else:
        production_exit = 0

    return max(agent_exit, integration_exit, benchmark_exit, certify_exit, production_exit)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
