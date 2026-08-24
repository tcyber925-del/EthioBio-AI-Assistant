"""LangSmith integration — agent tracing and evaluation.

Complements the existing OpenTelemetry / PipelineMonitor / Postgres trace
stack: LangSmith provides a hosted debugging + eval plane over the LangGraph
runs and raw-provider LLM calls.

Tracing is opt-in via settings. When enabled, graph runs are traced through
``langsmith.tracing_context`` (sampled at ``settings.langsmith_sampling_rate``)
and LLM calls through ``@langsmith.traceable``. Evaluation scores are attached
to the root run via the Feedback API.
"""

import os
import random
from contextlib import contextmanager
from typing import Optional

import structlog

from src.config import settings

logger = structlog.get_logger()

try:
    from langsmith import Client, tracing_context
    from langsmith.run_helpers import get_current_run_tree

    _LS_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - exercised when langsmith missing
    _LS_AVAILABLE = False
    Client = None  # type: ignore[assignment,misc]
    tracing_context = None  # type: ignore[assignment,misc]
    get_current_run_tree = None  # type: ignore[assignment,misc]

_client: Optional["Client"] = None
_client_configured = False


def setup_langsmith() -> Optional["Client"]:
    """Configure LangSmith env vars and return a cached Client.

    No-op (returns None) when tracing is disabled or no API key is set.
    Call once at application startup.
    """
    global _client, _client_configured
    if _client_configured:
        return _client
    _client_configured = True

    if not _LS_AVAILABLE or not settings.langsmith_tracing_enabled:
        return None
    if not settings.langsmith_api_key:
        logger.warning("langsmith_disabled_no_api_key")
        return None

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_workspace_id:
        os.environ["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id

    try:
        _client = Client(
            api_key=settings.langsmith_api_key,
            api_url=settings.langsmith_endpoint,
        )
    except Exception:
        logger.exception("langsmith_client_init_failed")
        return None

    logger.info(
        "langsmith_tracing_enabled",
        project=settings.langsmith_project,
        endpoint=settings.langsmith_endpoint,
        sampling_rate=settings.langsmith_sampling_rate,
    )
    return _client


def get_client() -> Optional["Client"]:
    """Lazily return the configured LangSmith client, or None."""
    if _client is None:
        setup_langsmith()
    return _client


def should_trace(force: bool = False) -> bool:
    """Sample whether the current invocation should be traced.

    Errors are always traced when force=True (mirrors EvalSampler's behavior).
    """
    if not settings.langsmith_tracing_enabled or not settings.langsmith_api_key:
        return False
    if force:
        return True
    return random.random() < settings.langsmith_sampling_rate  # noqa: S311 - sampling, not crypto


@contextmanager
def traced_run(
    enabled: Optional[bool] = None,
    force: bool = False,
    project_name: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """Context manager that enables/disables LangSmith tracing per invocation.

    Usage:
        with traced_run(metadata={"pipeline_trace_id": trace_id}):
            result = await graph.ainvoke(initial_state, config)

    Pass ``enabled`` to reuse a decision computed once with :func:`should_trace`;
    otherwise the sampling decision is made here.
    """
    if enabled is None:
        enabled = should_trace(force=force)
    if not enabled or tracing_context is None:
        yield None
        return
    with tracing_context(
        enabled=True,
        project_name=project_name or settings.langsmith_project,
        metadata=metadata,
    ):
        yield None


def capture_run_id() -> Optional[str]:
    """Return the current LangSmith run tree id, if any.

    Call inside a traced graph invocation to obtain the root run for
    correlation with PipelineMonitor traces and the Feedback API.

    Always returns a string: RunTree.id is a uuid.UUID, which would crash
    JSON serialization when persisted into agent_traces.event_metadata.
    """
    if not _LS_AVAILABLE or get_current_run_tree is None:
        return None
    try:
        run_tree = get_current_run_tree()
        return str(run_tree.id) if run_tree else None
    except Exception:
        return None


def post_feedback(run_id: str, results: list[dict]) -> None:
    """Attach evaluation scores to a LangSmith run via the Feedback API.

    results: list of {"dimension": str, "score": float, "explanation": str}.
    """
    client = get_client()
    if client is None or not run_id:
        return
    for result in results:
        try:
            client.create_feedback(
                run_id=run_id,
                key=result.get("dimension", "score"),
                score=result.get("score", 0.0),
                comment=result.get("explanation", ""),
            )
        except Exception:
            logger.warning(
                "langsmith_feedback_failed",
                run_id=run_id,
                dimension=result.get("dimension"),
                exc_info=True,
            )


__all__ = [
    "capture_run_id",
    "get_client",
    "post_feedback",
    "setup_langsmith",
    "should_trace",
    "traced_run",
]
