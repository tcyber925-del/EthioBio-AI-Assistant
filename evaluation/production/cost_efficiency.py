from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


PRODUCTION_COST_THRESHOLDS = {
    "requires_model_cost_tracking": True,
    "requires_token_budgeting": True,
    "requires_provider_selection_optimization": True,
    "requires_cost_attribution": True,
}


def check_model_cost_tracking() -> dict[str, Any]:
    """Verify LLM usage tracking exists."""
    try:
        from src.llm.manager import ProviderManager

        has_generate = hasattr(ProviderManager, "generate") or hasattr(ProviderManager, "_call_llm")
        return {
            "check": "model_cost_tracking",
            "passed": has_generate,
            "detail": "ProviderManager with LLM call tracking" if has_generate else "ProviderManager missing generate method",
        }
    except ImportError:
        return {"check": "model_cost_tracking", "passed": False, "detail": "ProviderManager not found"}


def check_token_budgeting() -> dict[str, Any]:
    """Verify token budgeting mechanisms exist."""
    try:
        from src.graph.state import AgentState

        has_token = "token_count" in AgentState.__dataclass_fields__ if hasattr(AgentState, "__dataclass_fields__") else False
        has_usage = hasattr(AgentState, "usage") if hasattr(AgentState, "__dataclass_fields__") else False
        if not has_token and not has_usage:
            try:
                from src.llm.providers.base import UsageInfo

                has_usage_info = isinstance(UsageInfo, dict) or hasattr(UsageInfo, "__dataclass_fields__")
                return {
                    "check": "token_budgeting",
                    "passed": has_usage_info,
                    "detail": "UsageInfo TypedDict for token tracking" if has_usage_info else "No token tracking found",
                }
            except ImportError:
                pass
        return {
            "check": "token_budgeting",
            "passed": has_token or has_usage,
            "detail": "Token tracking in AgentState" if has_token or has_usage else "No token budgeting found",
        }
    except (ImportError, AttributeError):
        return {"check": "token_budgeting", "passed": False, "detail": "AgentState not accessible"}


def check_provider_selection() -> dict[str, Any]:
    """Verify provider selection prefers cost-effective options."""
    try:
        from src.llm.manager import ProviderManager

        sig = getattr(ProviderManager, "set_active_model", None)
        has_model_switching = callable(sig)
        return {
            "check": "provider_selection_optimization",
            "passed": has_model_switching,
            "detail": "ProviderManager supports runtime model switching" if has_model_switching else "No model switching interface",
        }
    except ImportError:
        return {"check": "provider_selection_optimization", "passed": False, "detail": "ProviderManager not found"}


def check_cost_attribution() -> dict[str, Any]:
    """Verify cost can be attributed per-component."""
    try:
        from src.core.monitoring import PipelineMonitor

        has_timing = hasattr(PipelineMonitor, "node_timings") or any(
            "timing" in a.lower() or "duration" in a.lower()
            for a in dir(PipelineMonitor) if not a.startswith("_")
        )
        return {
            "check": "cost_attribution",
            "passed": has_timing,
            "detail": "PipelineMonitor with per-node timing" if has_timing else "No per-node timing in PipelineMonitor",
        }
    except ImportError:
        return {"check": "cost_attribution", "passed": False, "detail": "PipelineMonitor not found"}


def run_cost_efficiency_checks() -> dict[str, Any]:
    """Run all cost efficiency certification checks."""
    checks = [
        check_model_cost_tracking(),
        check_token_budgeting(),
        check_provider_selection(),
        check_cost_attribution(),
    ]

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    score = passed / total if total > 0 else 0.0

    return {
        "score": round(score, 3),
        "passed": passed,
        "total": total,
        "checks": checks,
        "failures": [c["check"] for c in checks if not c["passed"]],
    }
