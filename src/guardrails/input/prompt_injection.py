import re
from dataclasses import dataclass

from src.config import settings
from src.observability.guardrail_instrumentation import observe_guardrail


@dataclass
class PromptInjectionResult:
    detected: bool
    confidence: float
    pattern_match: str | None


class PromptInjectionDetector:
    PATTERNS: list[tuple[re.Pattern, float, str]] = [
        (
            re.compile(
                r"ignore\s+(all\s+)?(previous|prior|above|the)\s+(instructions|directives|commands)",
                re.IGNORECASE,
            ),
            0.8,
            "ignore_previous",
        ),
        (
            re.compile(
                r"you\s+are\s+(now|henceforth)\s+(an?\s+)?(AI|assistant|bot|model|system)",
                re.IGNORECASE,
            ),
            0.7,
            "role_override",
        ),
        (re.compile(r"system\s+prompt", re.IGNORECASE), 0.6, "system_prompt_reference"),
        (re.compile(r"new\s+(instructions|directive|rule)", re.IGNORECASE), 0.6, "new_instruction"),
        (
            re.compile(r"act\s+as\s+(if\s+)?(you(\u2019|')re|you\s+are)", re.IGNORECASE),
            0.6,
            "act_as",
        ),
        (re.compile(r"pretend\s+(to\s+be|that|you)", re.IGNORECASE), 0.6, "pretend"),
        (re.compile(r"from\s+now\s+on", re.IGNORECASE), 0.5, "from_now_on"),
        (re.compile(r"base64", re.IGNORECASE), 0.5, "base64_reference"),
        (re.compile(r"[A-Za-z0-9+/]{40,}={0,2}", re.IGNORECASE), 0.5, "base64_payload"),
        (
            re.compile(r"DAN|jailbreak|bypass\s+restrictions|unfiltered", re.IGNORECASE),
            0.9,
            "jailbreak_keyword",
        ),
        (
            re.compile(r"output\s+(without|censorship|filtering|restrictions)", re.IGNORECASE),
            0.7,
            "uncensored_request",
        ),
    ]

    def __init__(self):
        self._enabled = settings.prompt_injection_enabled
        self._threshold = settings.prompt_injection_threshold

    @observe_guardrail(module="prompt_injection", guardrail_type="input")
    def check(self, text: str) -> PromptInjectionResult:
        if not self._enabled:
            return PromptInjectionResult(detected=False, confidence=0.0, pattern_match=None)

        max_confidence = 0.0
        best_match = None

        for pattern, weight, name in self.PATTERNS:
            if pattern.search(text):
                if weight > max_confidence:
                    max_confidence = weight
                    best_match = name

        return PromptInjectionResult(
            detected=max_confidence >= self._threshold,
            confidence=max_confidence,
            pattern_match=best_match,
        )
