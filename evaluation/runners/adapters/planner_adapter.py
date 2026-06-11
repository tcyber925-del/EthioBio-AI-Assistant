from __future__ import annotations

import time
from typing import Any

from evaluation.datasets.schema import PlannerBenchmark
from evaluation.models import ComponentType, EvaluationResult
from evaluation.runners.adapter_base import EvalAdapter
from evaluation.scorers.plan_scorer import (
    score_complexity_estimation,
    score_task_f1,
    score_task_precision,
    score_task_recall,
)


class PlannerAdapter(EvalAdapter):
    component_type = ComponentType.PLANNER

    def __init__(self, planner_agent_class: Any):
        self._planner_cls = planner_agent_class

    async def execute(self, benchmark: Any, mock_llm: Any | None = None) -> EvaluationResult:
        bm = PlannerBenchmark.model_validate(benchmark)
        start = time.time()

        failures: list[str] = []
        try:
            agent = self._planner_cls(mock_llm)
            plan = await agent.generate_plan(bm.input_query)

            predicted_tasks = [t.objective for t in plan.subtasks]
            precision = score_task_precision(predicted_tasks, bm.expected_tasks)
            recall = score_task_recall(predicted_tasks, bm.expected_tasks)
            f1 = score_task_f1(predicted_tasks, bm.expected_tasks)
            complexity = score_complexity_estimation(
                plan.complexity_score < 0.5, bm.expected_complexity_low
            )

            if precision < 0.5:
                failures.append(f"low_precision:{precision:.2f}")
            if recall < 0.5:
                failures.append(f"low_recall:{recall:.2f}")
            if complexity < 1.0:
                failures.append("complexity_mismatch")

            score = 0.4 * f1 + 0.3 * precision + 0.3 * complexity

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return EvaluationResult(
                component=self.component_type,
                score=0.0,
                pass_status=False,
                latency_ms=latency_ms,
                failures=[f"execution_error:{e}"],
            )

        latency_ms = (time.time() - start) * 1000
        return EvaluationResult(
            component=self.component_type,
            score=round(score, 3),
            pass_status=len(failures) == 0,
            latency_ms=latency_ms,
            failures=failures,
            metrics={
                "task_precision": round(precision, 3),
                "task_recall": round(recall, 3),
                "task_f1": round(f1, 3),
                "complexity_accuracy": round(complexity, 3),
            },
        )
