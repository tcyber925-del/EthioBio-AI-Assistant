from __future__ import annotations

import time
from typing import Any

from evaluation.datasets.schema import LoopBenchmark
from evaluation.models import ComponentType, EvaluationResult
from evaluation.runners.adapter_base import EvalAdapter
from evaluation.scorers.accuracy_scorer import score_binary_accuracy


class LoopAdapter(EvalAdapter):
    component_type = ComponentType.RETRIEVAL_LOOP

    def __init__(self, loop_controller_class: Any):
        self._controller_cls = loop_controller_class

    async def execute(self, benchmark: Any, mock_llm: Any | None = None) -> EvaluationResult:
        bm = LoopBenchmark.model_validate(benchmark)
        start = time.time()

        failures: list[str] = []
        try:
            controller = self._controller_cls()
            mock_state = type(
                "MockState",
                (),
                {
                    "retrieval_iterations": bm.input_iterations,
                    "max_iterations": 5,
                    "coverage_score": bm.input_coverage_gain,
                    "previous_evidence_count": bm.input_previous_evidence_count,
                    "evidence_items": list(range(bm.input_evidence_count)),
                },
            )()

            decision = controller.decide(mock_state)

            continue_accuracy = score_binary_accuracy(
                decision.should_continue, bm.expected_should_continue
            )

            if continue_accuracy < 1.0:
                failures.append(
                    f"continue_mismatch:got={decision.should_continue},"
                    f"expected={bm.expected_should_continue}"
                )
            if decision.should_continue and bm.input_iterations >= 5:
                failures.append("infinite_loop_risk")

            score = continue_accuracy

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
                "continue_accuracy": round(continue_accuracy, 3),
                "iteration_count": float(bm.input_iterations),
            },
        )
