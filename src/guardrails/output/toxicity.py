import re
from dataclasses import dataclass, field

from src.config import settings
from src.observability.guardrail_instrumentation import observe_guardrail


@dataclass
class ToxicityResult:
    flagged: bool
    score: float
    categories: dict[str, float] = field(default_factory=dict)


TOXIC_PATTERNS: list[tuple[re.Pattern, float, str]] = [
    (re.compile(r"\b(kill|die|death|hurt|harm|pain)\b", re.IGNORECASE), 0.6, "violence"),
    (re.compile(r"\b(stupid|idiot|dumb|fool)\b", re.IGNORECASE), 0.5, "insult"),
    (re.compile(r"\b(hate|racist|sexist|discriminat)\w*\b", re.IGNORECASE), 0.8, "hate_speech"),
    (re.compile(r"\b(suicide|self-harm|self.harm)\b", re.IGNORECASE), 1.0, "self_harm"),
    (re.compile(r"\b(sex|sexual|porn|explicit)\b", re.IGNORECASE), 0.8, "sexual"),
    (re.compile(r"\b(drugs|cocaine|heroin|meth|weed|marijuana)\b", re.IGNORECASE), 0.7, "drugs"),
    (re.compile(r"\b(alcohol|beer|whiskey|vodka|wine)\b", re.IGNORECASE), 0.5, "alcohol"),
    (re.compile(r"\b(weapon|gun|bomb|knife|sword|explosive)\b", re.IGNORECASE), 0.6, "weapons"),
]


class ToxicityDetector:
    def __init__(self):
        self._enabled = settings.output_toxicity_enabled

    @observe_guardrail(module="toxicity_detector", guardrail_type="output")
    def check(self, text: str) -> ToxicityResult:
        if not self._enabled:
            return ToxicityResult(flagged=False, score=0.0)

        max_score = 0.0
        categories: dict[str, float] = {}

        for pattern, weight, name in TOXIC_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                raw_score = min(1.0, weight * len(matches) * 0.5)
                categories.setdefault(name, 0.0)
                categories[name] = max(categories.get(name, 0.0), raw_score)
                if raw_score > max_score:
                    max_score = raw_score

        return ToxicityResult(
            flagged=max_score >= 0.7,
            score=max_score,
            categories=categories,
        )
