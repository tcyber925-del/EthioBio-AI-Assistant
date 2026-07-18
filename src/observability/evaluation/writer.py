from opentelemetry import trace

from src.observability.evaluation.dimensions import EvalDimension
from src.observability.evaluation.judge import LLMJudge
from src.observability.metrics import set_gauge
from src.observability.tracing import (
    GEN_AI_EVALUATION_EXPLANATION,
    GEN_AI_EVALUATION_LABEL,
    GEN_AI_EVALUATION_SCORE,
)


def attach_eval_to_trace(dimension: str, score: float, explanation: str = "") -> None:
    current_span = trace.get_current_span()
    if not current_span or not current_span.is_recording():
        return
    current_span.set_attribute(f"{GEN_AI_EVALUATION_SCORE}.{dimension}", score)
    current_span.set_attribute(f"{GEN_AI_EVALUATION_LABEL}.{dimension}", f"{score:.2f}")
    if explanation:
        current_span.set_attribute(f"{GEN_AI_EVALUATION_EXPLANATION}.{dimension}", explanation)
    set_gauge(f"gen_ai.evaluation.{dimension}_score", score)


async def evaluate_and_write(
    judge: LLMJudge,
    question: str,
    response: str,
    context: str = "",
    dimensions: list[EvalDimension] | None = None,
) -> list[dict]:
    from src.observability.evaluation.dimensions import DIMENSIONS

    dims = dimensions or DIMENSIONS
    results: list[dict] = []
    for dim in dims:
        result = await judge.score(dim, question, response, context)
        attach_eval_to_trace(dim.name, result["score"], result.get("explanation", ""))
        results.append({"dimension": dim.name, **result})
    return results
