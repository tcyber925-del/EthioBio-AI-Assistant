from __future__ import annotations

import time
from typing import Any

from evaluation.datasets.schema import FanoutBenchmark
from evaluation.models import ComponentType, EvaluationResult
from evaluation.runners.adapter_base import EvalAdapter
from evaluation.scorers.accuracy_scorer import score_batch_accuracy


class FanoutAdapter(EvalAdapter):
    component_type = ComponentType.SEARCH_FANOUT

    def __init__(self, fanout_agent_class: Any):
        self._fanout_cls = fanout_agent_class

    async def execute(self, benchmark: Any, mock_llm: Any | None = None) -> EvaluationResult:
        bm = FanoutBenchmark.model_validate(benchmark)
        start = time.time()

        failures: list[str] = []
        try:
            agent = self._fanout_cls()
            tasks, strategy = agent.plan(bm.input_query_groups)

            task_sources = [t.source for t in (tasks or [])]
            correct_routes = [
                1 if src in bm.expected_correct_routes else 0
                for src in task_sources
            ]
            expected_correct = [1] * len(correct_routes)

            source_accuracy = score_batch_accuracy(
                [bool(c) for c in correct_routes],
                [bool(e) for e in expected_correct],
            ) if correct_routes else 0.0

            if source_accuracy < 0.8:
                failures.append(f"source_accuracy:{source_accuracy:.2f}")
            if len(task_sources) < bm.expected_source_count:
                failures.append(
                    f"source_count:{len(task_sources)}<{bm.expected_source_count}"
                )

            score = source_accuracy

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
                "source_accuracy": round(source_accuracy, 3),
                "source_count": float(len(task_sources)),
            },
        )
