from typing import Any

import structlog

logger = structlog.get_logger()


def log_event(
    event: str,
    domain: str = "system",
    module: str = "",
    outcome: str = "info",
    duration_ms: float | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    user_id: str | None = None,
    details: dict[str, Any] | None = None,
    level: str = "info",
) -> dict:
    """Emit a structured log event with consistent schema."""
    payload: dict = {
        "domain": domain,
        "module": module,
        "outcome": outcome,
    }
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    if trace_id is not None:
        payload["trace_id"] = trace_id
    if span_id is not None:
        payload["span_id"] = span_id
    if user_id is not None:
        payload["user_id"] = user_id
    if details:
        payload["details"] = details

    level_fn = {
        "debug": logger.debug,
        "info": logger.info,
        "warning": logger.warning,
        "error": logger.error,
        "critical": logger.critical,
    }.get(level, logger.info)

    level_fn(event, **payload)
    return payload
