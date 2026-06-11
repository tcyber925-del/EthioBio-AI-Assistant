from __future__ import annotations

import time
from typing import Any

from evaluation.datasets.schema import TutorBenchmark
from evaluation.models import ComponentType, EvaluationResult
from evaluation.runners.adapter_base import EvalAdapter
from evaluation.scorers.grounding_scorer import (
    score_citation_fidelity,
    score_hallucination_absence,
)


class TutorAdapter(EvalAdapter):
    component_type = ComponentType.TUTOR

    def __init__(self, tutor_agent_class: Any):
        self._tutor_cls = tutor_agent_class

    async def execute(self, benchmark: Any, mock_llm: Any | None = None) -> EvaluationResult:
        bm = TutorBenchmark.model_validate(benchmark)
        start = time.time()

        failures: list[str] = []
        try:
            agent = self._tutor_cls(mock_llm)
            response = await agent.generate(
                user_message=bm.input_query,
                evidence_items=bm.input_evidence_items,
                evidence_synthesis="",
            )

            response_citations = (
                response.citations if hasattr(response, "citations") else []
            )
            hallucinated = (
                response.hallucinated_claims if hasattr(response, "hallucinated_claims") else 0
            )
            total_claims = len(response_citations) + hallucinated

            citation_fidelity = score_citation_fidelity(
                response_citations, bm.expected_citations
            )
            hallucination_score = score_hallucination_absence(
                hallucinated, total_claims
            )

            if citation_fidelity < bm.expected_grounding_min:
                failures.append(
                    f"low_grounding:{citation_fidelity:.2f}<{bm.expected_grounding_min}"
                )
            if bm.expected_no_hallucination and hallucination_score < 1.0:
                failures.append(f"hallucination_detected:{hallucinated}/{total_claims}")

            score = 0.7 * citation_fidelity + 0.3 * hallucination_score

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
                "citation_fidelity": round(citation_fidelity, 3),
                "hallucination_score": round(hallucination_score, 3),
            },
        )
