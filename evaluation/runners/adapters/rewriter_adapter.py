from __future__ import annotations

import time
from typing import Any

from evaluation.datasets.schema import RewriterBenchmark
from evaluation.models import ComponentType, EvaluationResult
from evaluation.runners.adapter_base import EvalAdapter
from evaluation.scorers.diversity_scorer import (
    score_query_count,
    score_redundancy,
    score_source_diversity,
)


class RewriterAdapter(EvalAdapter):
    component_type = ComponentType.QUERY_REWRITER

    def __init__(self, rewriter_agent_class: Any):
        self._rewriter_cls = rewriter_agent_class

    async def execute(self, benchmark: Any, mock_llm: Any | None = None) -> EvaluationResult:
        bm = RewriterBenchmark.model_validate(benchmark)
        start = time.time()

        failures: list[str] = []
        try:
            agent = self._rewriter_cls(mock_llm)
            bundle = await agent.rewrite(bm.input_query, bm.input_subtasks)

            actual_count = len(bundle.queries) if hasattr(bundle, "queries") else 1
            actual_sources = (
                bundle.source_types if hasattr(bundle, "source_types") else []
            )

            count_score = score_query_count(actual_count, bm.expected_min_queries)
            diversity_score = score_source_diversity(actual_sources, bm.expected_diverse_sources)
            redundancy_score = score_redundancy(0.0, bm.expected_max_redundancy)

            if count_score < 1.0:
                failures.append(f"query_count:{actual_count}<{bm.expected_min_queries}")
            if diversity_score < 1.0:
                failures.append("insufficient_source_diversity")

            score = 0.4 * count_score + 0.3 * diversity_score + 0.3 * redundancy_score

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
                "query_count_score": round(count_score, 3),
                "diversity_score": round(diversity_score, 3),
                "redundancy_score": round(redundancy_score, 3),
            },
        )
