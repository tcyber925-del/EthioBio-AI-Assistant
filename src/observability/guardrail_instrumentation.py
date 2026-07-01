import functools
import time

from src.observability.health import health_registry
from src.observability.metrics import inc_counter, set_gauge
from src.observability.structured_logging import log_event
from src.observability.tracing import (
    GUARDRAIL_MODULE,
    GUARDRAIL_OUTCOME,
    GUARDRAIL_TRIGGERED,
    GUARDRAIL_TYPE,
    tracer,
)


def observe_guardrail(module: str, guardrail_type: str = "output"):
    """Decorator — wrap a guardrail function with OTel span + metrics + logging + health."""

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            with tracer.start_as_current_span(f"guardrail.{module}") as span:
                span.set_attribute(GUARDRAIL_MODULE, module)
                span.set_attribute(GUARDRAIL_TYPE, guardrail_type)
                try:
                    result = await func(*args, **kwargs)
                    triggered = _is_triggered(result)
                    span.set_attribute(GUARDRAIL_OUTCOME, "flagged" if triggered else "passed")
                    span.set_attribute(GUARDRAIL_TRIGGERED, triggered)
                    _record_guardrail_metrics(module, triggered, start)
                    return result
                except Exception as e:
                    span.set_attribute(GUARDRAIL_OUTCOME, "error")
                    span.record_exception(e)
                    _record_guardrail_metrics(module, False, start, error=True)
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            with tracer.start_as_current_span(f"guardrail.{module}") as span:
                span.set_attribute(GUARDRAIL_MODULE, module)
                span.set_attribute(GUARDRAIL_TYPE, guardrail_type)
                try:
                    result = func(*args, **kwargs)
                    triggered = _is_triggered(result)
                    span.set_attribute(GUARDRAIL_OUTCOME, "flagged" if triggered else "passed")
                    span.set_attribute(GUARDRAIL_TRIGGERED, triggered)
                    _record_guardrail_metrics(module, triggered, start)
                    return result
                except Exception as e:
                    span.set_attribute(GUARDRAIL_OUTCOME, "error")
                    span.record_exception(e)
                    _record_guardrail_metrics(module, False, start, error=True)
                    raise

        return async_wrapper if _is_async(func) else sync_wrapper

    return decorator


def _is_triggered(result) -> bool:
    if result is None:
        return False
    if isinstance(result, bool):
        return result
    if hasattr(result, "blocked") and result.blocked:
        return True
    if hasattr(result, "flagged") and result.flagged:
        return True
    if hasattr(result, "detected") and result.detected:
        return True
    if hasattr(result, "passed") and not result.passed:
        return True
    if hasattr(result, "on_topic") and not result.on_topic:
        return True
    if hasattr(result, "allowed") and not result.allowed:
        return True
    if isinstance(result, dict):
        for key in ("triggered", "flagged", "blocked", "detected"):
            if result.get(key, False):
                return True
    return isinstance(result, str) and len(result) > 0


def _record_guardrail_metrics(
    module: str, triggered: bool, start: float, error: bool = False
) -> None:
    duration_ms = (time.time() - start) * 1000
    inc_counter("guardrail.invocations", labels={"module": module})
    if health_registry:
        health_registry.record_request(module, error=error)
        if triggered:
            health_registry.set_status(
                module, "degraded", details=f"Last: flagged at {duration_ms:.0f}ms"
            )
    log_event(
        event="guardrail_check",
        domain="guardrails",
        module=module,
        outcome="triggered" if triggered else ("error" if error else "passed"),
        duration_ms=duration_ms,
        details={"triggered": triggered, "error": error},
    )
    set_gauge(f"guardrail.{module}.duration_ms", duration_ms)
    set_gauge(f"guardrail.{module}.triggered", 1.0 if triggered else 0.0)


def _is_async(func):
    import asyncio
    return asyncio.iscoroutinefunction(func)
