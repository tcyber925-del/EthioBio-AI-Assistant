"""OTel GenAI semantic convention helpers for EthioSci spans.

Aligns with gen_ai.* attribute naming from OpenTelemetry GenAI semconv (v1.37+).
"""

from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.trace import Span

    _OTEL_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - exercised when otel not installed
    _OTEL_AVAILABLE = False
    trace = None
    Span = object


class _NullSpan:
    def set_attribute(self, *args: object, **kwargs: object) -> None:
        pass

    def __enter__(self) -> "_NullSpan":
        return self

    def __exit__(self, *exc: object) -> None:
        pass


class _NullTracer:
    @contextmanager
    def start_as_current_span(self, *args: object, **kwargs: object):
        yield _NullSpan()

    def start_span(self, *args: object, **kwargs: object) -> _NullSpan:
        return _NullSpan()


if _OTEL_AVAILABLE:
    tracer = trace.get_tracer_provider().get_tracer(__name__)
else:
    tracer = _NullTracer()

# Well-known span attribute names following OTel GenAI semconv
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_PROVIDER_NAME = "gen_ai.provider.name"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GEN_AI_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
GEN_AI_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
GEN_AI_EVALUATION_SCORE = "gen_ai.evaluation.score.value"
GEN_AI_EVALUATION_LABEL = "gen_ai.evaluation.score.label"
GEN_AI_EVALUATION_EXPLANATION = "gen_ai.evaluation.explanation"

# Custom guardrail span attributes (extended namespace)
GUARDRAIL_TYPE = "guardrail.type"
GUARDRAIL_MODULE = "guardrail.module"
GUARDRAIL_OUTCOME = "guardrail.outcome"
GUARDRAIL_TRIGGERED = "gen_ai.guardrail.triggered"


def start_guardrail_span(guardrail_type: str, module: str, outcome: str = "pass") -> Span:
    """Create a guardrail sub-span attached to the current trace."""
    span = tracer.start_span(f"guardrail.{guardrail_type}")
    span.set_attribute(GUARDRAIL_TYPE, guardrail_type)
    span.set_attribute(GUARDRAIL_MODULE, module)
    span.set_attribute(GUARDRAIL_OUTCOME, outcome)
    span.set_attribute(GUARDRAIL_TRIGGERED, outcome == "block")
    return span


def set_eval_on_span(
    span: Span, dimension: str, score: float, explanation: str | None = None
) -> None:
    """Attach evaluation score to an existing span (eval-as-span-attribute pattern)."""
    span.set_attribute(f"gen_ai.evaluation.{dimension}.score", score)
    if explanation:
        span.set_attribute(f"gen_ai.evaluation.{dimension}.explanation", explanation)
