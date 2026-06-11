from __future__ import annotations

import time
from typing import Any

from evaluation.datasets.schema import ContextBenchmark
from evaluation.models import ComponentType, EvaluationResult
from evaluation.runners.adapter_base import EvalAdapter
from evaluation.scorers.accuracy_scorer import score_binary_accuracy


class ContextAdapter(EvalAdapter):
    component_type = ComponentType.SUFFICIENT_CONTEXT

    def __init__(self, evaluate_sufficiency_fn: Any):
        self._eval_fn = evaluate_sufficiency_fn

    async def execute(self, benchmark: Any, mock_llm: Any | None = None) -> EvaluationResult:
        bm = ContextBenchmark.model_validate(benchmark)
        start = time.time()

        failures: list[str] = []
        try:
            mock_state = {
                "subtasks": [],
                "rewritten_queries": [],
                "retrieved_chunks": [{}] * bm.input_evidence_count,
                "coverage_score": bm.input_coverage_score,
                "retrieval_iterations": 0,
                "previous_evidence_count": bm.input_previous_evidence_count,
                "evidence_items": [],
                "evidence_ids": [],
                "max_iterations": 3,
            }

            result = self._eval_fn(mock_state)

            sufficiency_accuracy = score_binary_accuracy(
                result.sufficient, bm.expected_sufficient
            )

            if sufficiency_accuracy < 1.0:
                failures.append(
                    f"sufficiency_mismatch:got={result.sufficient},expected={bm.expected_sufficient}"
                )

            score = sufficiency_accuracy

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
                "sufficiency_accuracy": round(sufficiency_accuracy, 3),
                "evidence_count": float(bm.input_evidence_count),
            },
        )
