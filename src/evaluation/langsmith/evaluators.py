"""Evaluators for LangSmith datasets.

Reuses the in-house LLMJudge (faithfulness, relevance, safety, helpfulness)
and adds a deterministic topic-coverage check against the scenario's
``expected_topics``.
"""

from typing import Optional

from src.observability.evaluation.dimensions import EvalDimension
from src.observability.evaluation.judge import LLMJudge


def topic_coverage_evaluator(run, example) -> dict:
    """Fraction of expected topics mentioned in the answer.

    Uses the dataset's ``expected_topics`` output (from the YAML scenarios)
    which the offline BenchmarkRunner never actually validated.
    """
    expected = set((example.outputs or {}).get("expected_topics") or [])
    answer = ((run.outputs or {}).get("answer") or "").lower()
    if not expected:
        return {"key": "topic_coverage", "score": 1.0}
    covered = sum(1 for topic in expected if topic.lower() in answer)
    return {"key": "topic_coverage", "score": round(covered / len(expected), 3)}


def llm_judge_evaluator(dimension: EvalDimension, judge: Optional[LLMJudge] = None):
    """Factory for an LLM-as-a-judge evaluator over one EvalDimension."""

    async def _evaluator(run, example) -> dict:
        active_judge = judge or LLMJudge()
        question = (example.inputs or {}).get("question", "")
        answer = (run.outputs or {}).get("answer", "")
        context = (run.outputs or {}).get("context", "")
        result = await active_judge.score(dimension, question, answer, context)
        return {
            "key": dimension.name,
            "score": result["score"],
            "comment": result.get("explanation", ""),
        }

    return _evaluator


def default_evaluators() -> list:
    """All evaluators: topic coverage + the four judge dimensions."""
    from src.observability.evaluation.dimensions import DIMENSIONS

    return [topic_coverage_evaluator] + [llm_judge_evaluator(dim) for dim in DIMENSIONS]
