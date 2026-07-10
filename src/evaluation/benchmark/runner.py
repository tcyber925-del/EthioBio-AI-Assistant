import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import yaml

from src.evaluation.benchmark.models import BenchmarkReport, ScenarioResult
from src.evaluation.benchmark.regression import DEFAULT_TOLERANCE, RegressionDetector

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    def __init__(
        self,
        scenarios_dir: str,
        baselines_dir: str,
        regression_tolerance: float = DEFAULT_TOLERANCE,
    ):
        self.scenarios_dir = scenarios_dir
        self.baselines_dir = baselines_dir
        self.regression_tolerance = regression_tolerance
        self.scenarios: list[dict] = []
        self._load_scenarios()

    def _load_scenarios(self) -> None:
        scenarios_path = Path(self.scenarios_dir)
        if not scenarios_path.exists():
            logger.warning("scenarios_dir not found: %s", self.scenarios_dir)
            return

        for f in sorted(scenarios_path.glob("*.yaml")):
            with open(f) as fh:
                data = yaml.safe_load(fh)
                for s in data.get("scenarios", []):
                    s["grade_level"] = s.get("grade_level", data.get("grade_level", 8))
                    s["language"] = s.get("language", data.get("language", "en"))
                    self.scenarios.append(s)

    def _load_baselines(self) -> dict:
        baselines_path = Path(self.baselines_dir)
        baselines: dict = {}
        if not baselines_path.exists():
            return baselines
        for f in sorted(baselines_path.glob("*.json")):
            with open(f) as fh:
                data = json.load(fh)
                baselines.update(data.get("scenarios", data))
        return baselines

    def _save_baselines(self, results: list[ScenarioResult]) -> None:
        baselines_path = Path(self.baselines_dir)
        baselines_path.mkdir(parents=True, exist_ok=True)

        scenarios_by_group: dict[str, list[ScenarioResult]] = {}
        for r in results:
            s = next((s for s in self.scenarios if s["id"] == r.scenario_id), None)
            tag = "default"
            if s:
                tags = s.get("tags", [])
                tag = tags[0] if tags else "default"
            scenarios_by_group.setdefault(tag, []).append(r)

        for group, group_results in scenarios_by_group.items():
            group_baselines = {}
            for r in group_results:
                group_baselines[r.scenario_id] = RegressionDetector.generate_baseline(
                    r.metrics,
                    self.regression_tolerance,
                )
            filepath = baselines_path / f"{group}.json"
            with open(filepath, "w") as f:
                json.dump({"scenarios": group_baselines}, f, indent=2)

    async def _run_pipeline(self, scenario: dict) -> Any:
        from src.graph.orchestrator import run_graph

        return await run_graph(
            user_message=scenario["question"],
            grade_level=scenario.get("grade_level", 8),
            language=scenario.get("language", "en"),
        )

    async def run_all(
        self,
        filters: Optional[list[str]] = None,
        update_baselines: bool = False,
    ) -> BenchmarkReport:
        scenarios_to_run = self.scenarios
        if filters:
            scenarios_to_run = [
                s for s in self.scenarios if any(t in s.get("tags", []) for t in filters)
            ]

        results: list[ScenarioResult] = []

        for scenario in scenarios_to_run:
            start = time.time()
            try:
                state = await self._run_pipeline(scenario)
                duration_ms = (time.time() - start) * 1000

                metrics = {
                    "hallucination_rate": state.get("hallucination_rate", 0.0),
                    "groundedness_score": state.get("groundedness_score", 0.0),
                    "coverage_score": state.get("coverage_score", 0.0),
                    "duration_ms": duration_ms,
                    "requires_teacher_review": state.get("requires_teacher_review", False),
                }

                results.append(
                    ScenarioResult(
                        scenario_id=scenario["id"],
                        question=scenario["question"],
                        passed=True,
                        metrics=metrics,
                        duration_ms=duration_ms,
                    )
                )
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.error("scenario %s failed: %s", scenario["id"], e)
                results.append(
                    ScenarioResult(
                        scenario_id=scenario["id"],
                        question=scenario["question"],
                        passed=False,
                        error=str(e),
                        duration_ms=duration_ms,
                    )
                )

        if update_baselines:
            self._save_baselines(results)

        baselines = self._load_baselines()
        detector = RegressionDetector(baselines)
        regressions: list[str] = []
        for r in results:
            issues = detector.check(r.scenario_id, r.metrics)
            regressions.extend(issues)
            if issues:
                r.passed = False

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        agg = {}
        if results:
            agg = {
                "avg_hallucination_rate": round(
                    sum(r.metrics.get("hallucination_rate", 0) for r in results) / total,
                    3,
                ),
                "avg_groundedness": round(
                    sum(r.metrics.get("groundedness_score", 0) for r in results) / total,
                    3,
                ),
                "avg_coverage": round(
                    sum(r.metrics.get("coverage_score", 0) for r in results) / total,
                    3,
                ),
                "avg_duration_ms": round(
                    sum(r.duration_ms for r in results) / total,
                    1,
                ),
            }

        return BenchmarkReport(
            total_scenarios=total,
            passed=passed,
            failed=total - passed,
            results=results,
            aggregate_metrics=agg,
            regressions=regressions,
        )
