from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from evaluation.datasets.schema import (
    ContextBenchmark,
    EvidenceBenchmark,
    FanoutBenchmark,
    LoopBenchmark,
    PlannerBenchmark,
    RewriterBenchmark,
    TutorBenchmark,
)
from evaluation.models import ComponentType, EvalSummary, EvaluationResult
from evaluation.runners.adapter_base import EvalAdapter

logger = logging.getLogger(__name__)

SCHEMA_MAP: dict[ComponentType, type] = {
    ComponentType.PLANNER: PlannerBenchmark,
    ComponentType.QUERY_REWRITER: RewriterBenchmark,
    ComponentType.SEARCH_FANOUT: FanoutBenchmark,
    ComponentType.EVIDENCE_GRAPH: EvidenceBenchmark,
    ComponentType.SUFFICIENT_CONTEXT: ContextBenchmark,
    ComponentType.RETRIEVAL_LOOP: LoopBenchmark,
    ComponentType.TUTOR: TutorBenchmark,
}


class EvalRunner:
    def __init__(
        self,
        datasets_dir: str,
        adapters: dict[ComponentType, EvalAdapter] | None = None,
        mock_llm: Any | None = None,
        regression_baselines: dict[str, dict] | None = None,
    ):
        self.datasets_dir = Path(datasets_dir)
        self.adapters = adapters or {}
        self.mock_llm = mock_llm
        self.regression_baselines = regression_baselines or {}

    def register_adapter(self, component: ComponentType, adapter: EvalAdapter) -> None:
        self.adapters[component] = adapter

    def _load_dataset(self, component: ComponentType) -> list[dict]:
        filepath = self.datasets_dir / f"{component.value}.json"
        if not filepath.exists():
            logger.warning("dataset not found: %s", filepath)
            return []
        with open(filepath) as f:
            return json.load(f)

    async def evaluate_component(
        self, component: ComponentType, adapter: EvalAdapter | None = None
    ) -> EvaluationResult:
        adapter = adapter or self.adapters.get(component)
        if not adapter:
            return EvaluationResult(
                component=component,
                score=0.0,
                pass_status=False,
                failures=["no_adapter_registered"],
            )

        dataset = self._load_dataset(component)
        if not dataset:
            return EvaluationResult(
                component=component,
                score=0.0,
                pass_status=False,
                failures=["no_dataset_found"],
            )

        scores: list[float] = []
        all_failures: list[str] = []
        all_metrics: dict[str, float] = {}

        for entry in dataset:
            if entry.get("skip"):
                continue
            result = await adapter.execute(entry, self.mock_llm)
            scores.append(result.score)
            all_failures.extend(result.failures)
            for k, v in result.metrics.items():
                all_metrics[k] = all_metrics.get(k, 0.0) + v

        count = len(scores)
        if count == 0:
            return EvaluationResult(
                component=component,
                score=0.0,
                pass_status=False,
                failures=["no_non_skipped_entries"],
            )

        avg_score = sum(scores) / count
        for k in all_metrics:
            all_metrics[k] = round(all_metrics[k] / count, 3)

        baseline = self.regression_baselines.get(component.value, {})
        baseline_score = baseline.get("score", 0.0)
        if baseline_score > 0 and (baseline_score - avg_score) > 0.05:
            all_failures.append(
                f"regression:{avg_score:.3f}<baseline:{baseline_score:.3f}"
            )

        return EvaluationResult(
            component=component,
            score=round(avg_score, 3),
            pass_status=len(all_failures) == 0,
            metrics=all_metrics,
            failures=all_failures,
        )

    async def evaluate_all(
        self,
        filters: list[ComponentType] | None = None,
    ) -> EvalSummary:
        components = filters or list(ComponentType)
        results: list[EvaluationResult] = []
        total_score = 0.0
        component_scores: dict[str, float] = {}
        all_regressions: list[str] = []

        for component in components:
            adapter = self.adapters.get(component)
            if not adapter:
                logger.warning("no adapter for %s, skipping", component)
                continue
            result = await self.evaluate_component(component, adapter)
            results.append(result)
            total_score += result.score
            component_scores[component.value] = result.score
            if any("regression" in f for f in result.failures):
                all_regressions.extend(
                    [f"{component.value}:{f}" for f in result.failures if "regression" in f]
                )

        count = len(results)
        return EvalSummary(
            total_components=count,
            passed=sum(1 for r in results if r.pass_status),
            failed=sum(1 for r in results if not r.pass_status),
            aggregate_score=round(total_score / count, 3) if count else 0.0,
            results=results,
            regressions=all_regressions,
            component_scores=component_scores,
        )
