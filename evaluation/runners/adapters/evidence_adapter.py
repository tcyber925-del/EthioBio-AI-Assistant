from __future__ import annotations

import time
from typing import Any

from evaluation.datasets.schema import EvidenceBenchmark
from evaluation.models import ComponentType, EvaluationResult
from evaluation.runners.adapter_base import EvalAdapter
from evaluation.scorers.accuracy_scorer import score_binary_accuracy


class EvidenceAdapter(EvalAdapter):
    component_type = ComponentType.EVIDENCE_GRAPH

    def __init__(self, evidence_graph_class: Any, db_session_factory: Any | None = None):
        self._graph_cls = evidence_graph_class
        self._db_factory = db_session_factory

    async def execute(self, benchmark: Any, mock_llm: Any | None = None) -> EvaluationResult:
        bm = EvidenceBenchmark.model_validate(benchmark)
        start = time.time()

        failures: list[str] = []
        try:
            graph = self._graph_cls()
            internal_session_id = await graph.create_session(
                session_id="eval-session",
                trace_id=f"eval-{bm.id}",
                user_id="eval-user",
            )

            for chunk in bm.input_chunks:
                await graph.add(
                    evidence=chunk,
                    internal_session_id=internal_session_id,
                )

            coverage = await graph.get_coverage(
                session_id="eval-session",
                question="eval question",
            )

            deduped_count = len(bm.input_chunks) - (0 if coverage is None else 0)
            dedup_accuracy = score_binary_accuracy(
                deduped_count == bm.expected_deduped_count,
                True,
            )
            coverage_met = (
                (coverage.score >= bm.expected_coverage_min)
                if coverage and hasattr(coverage, "score")
                else False
            )
            coverage_score = 1.0 if coverage_met else 0.0

            if dedup_accuracy < 1.0:
                failures.append(
                    f"dedup_mismatch:{deduped_count}!={bm.expected_deduped_count}"
                )
            if not coverage_met:
                failures.append(
                    f"coverage_below_min:{coverage.score if coverage else 0:.2f}"
                )

            score = 0.6 * dedup_accuracy + 0.4 * coverage_score

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
                "dedup_accuracy": round(dedup_accuracy, 3),
                "coverage_score": round(coverage_score, 3),
            },
        )
