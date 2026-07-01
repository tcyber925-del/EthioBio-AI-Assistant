from dataclasses import dataclass, field
from typing import Any

from src.config import settings
from src.observability.guardrail_instrumentation import observe_guardrail

ALLOWED_TOOLS = frozenset(
    {
        "retrieve_curriculum",
        "generate_quiz",
        "create_diagram",
        "lookup_definition",
        "search_biology_topic",
        "get_student_progress",
        "recommend_next_topic",
        "check_prerequisite",
    }
)

MAX_TOOL_CALLS = 20
MAX_STEPS = 50


@dataclass
class ToolValidationResult:
    allowed: bool
    reason: str = ""
    sanitized_args: dict[str, Any] | None = None


@dataclass
class ToolGuardResult:
    passed: bool
    blocked: bool
    reasons: list[str] = field(default_factory=list)


class ToolGuard:
    def __init__(self):
        self._enabled = settings.tool_guard_enabled

    @observe_guardrail(module="tool_guard_validate", guardrail_type="action")
    def validate_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> ToolValidationResult:
        if not self._enabled:
            return ToolValidationResult(allowed=True)

        if tool_name not in ALLOWED_TOOLS:
            return ToolValidationResult(
                allowed=False,
                reason=f"Tool '{tool_name}' is not in the allowed list",
            )

        sanitized = dict(args)
        for key in list(sanitized.keys()):
            val = sanitized[key]
            if isinstance(val, str) and len(val) > 2000:
                sanitized[key] = val[:2000]

        return ToolValidationResult(allowed=True, sanitized_args=sanitized)

    def check_step_limits(
        self,
        tool_call_count: int,
        step_count: int,
    ) -> list[str]:
        reasons: list[str] = []
        if tool_call_count > MAX_TOOL_CALLS:
            reasons.append(f"Tool call limit exceeded: {tool_call_count} > {MAX_TOOL_CALLS}")
        if step_count > MAX_STEPS:
            reasons.append(f"Step limit exceeded: {step_count} > {MAX_STEPS}")
        return reasons

    @observe_guardrail(module="tool_guard_response", guardrail_type="action")
    def check_response(
        self,
        tool_name: str,
        args: dict[str, Any],
        response: Any,
    ) -> ToolValidationResult:
        if not self._enabled:
            return ToolValidationResult(allowed=True)

        if isinstance(response, str) and len(response) > 50000:
            return ToolValidationResult(
                allowed=False,
                reason=f"Response from '{tool_name}' exceeds size limit",
            )

        if tool_name in ("generate_quiz", "create_diagram"):
            if isinstance(response, dict):
                allowed_keys = {
                    "questions",
                    "title",
                    "diagram_svg",
                    "labels",
                    "type",
                    "content",
                    "metadata",
                }
                response_keys = set(response.keys())
                forbidden = response_keys - allowed_keys
                if forbidden:
                    return ToolValidationResult(
                        allowed=False,
                        reason=f"Response from '{tool_name}' contains unexpected keys: {forbidden}",
                    )

        return ToolValidationResult(allowed=True)
