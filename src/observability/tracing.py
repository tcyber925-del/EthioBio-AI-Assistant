"""
LangSmith tracing for EthioBio AI Assistant.

Provides decorators and helpers for tracing requests through the graph.
Skips tracing if LANGCHAIN_API_KEY is not set (graceful fallback).
"""

import functools
import os
from typing import Callable, Optional

import structlog

logger = structlog.get_logger()

_initialized = False


def init_tracing(project_name: str = "ethiobio-ai-assistant") -> bool:
    global _initialized
    if _initialized:
        return True

    api_key = os.environ.get("LANGCHAIN_API_KEY")
    if not api_key:
        logger.info("tracing_disabled - set LANGCHAIN_API_KEY to enable LangSmith")
        _initialized = True
        return False

    try:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_PROJECT", project_name)
        _initialized = True
        logger.info("langsmith_tracing_enabled", project=project_name)
        return True
    except Exception as e:
        logger.warning("tracing_init_failed", error=str(e))
        return False


def traceable(name: Optional[str] = None) -> Callable:
    """Decorator that wraps a function with LangSmith tracing if available."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            init_tracing()
            try:
                from langsmith import traceable as ls_traceable
                traced = ls_traceable(name=name or func.__name__)(func)
                return await traced(*args, **kwargs)
            except (ImportError, Exception):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            init_tracing()
            try:
                from langsmith import traceable as ls_traceable
                traced = ls_traceable(name=name or func.__name__)(func)
                return traced(*args, **kwargs)
            except (ImportError, Exception):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    import asyncio
    return decorator


class TraceContext:
    """Context manager for tracing a block of code."""
    def __init__(self, name: str, metadata: Optional[dict] = None):
        self.name = name
        self.metadata = metadata or {}

    async def __aenter__(self):
        init_tracing()
        self.run_id = None
        try:
            from langsmith.run_trees import RunTree
            self._run = RunTree(name=self.name, inputs=self.metadata)
            self._run.post()
            self.run_id = self._run.id
        except Exception:
            pass
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, '_run'):
            try:
                self._run.end(outputs={"success": exc_type is None})
                self._run.patch()
            except Exception:
                pass
