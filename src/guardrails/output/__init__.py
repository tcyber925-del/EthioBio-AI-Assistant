from dataclasses import dataclass, field

from src.guardrails.output.pii_scanner import PIIScanner
from src.guardrails.output.topic_enforcer import TopicEnforcer
from src.guardrails.output.toxicity import ToxicityDetector
from src.observability.guardrail_instrumentation import observe_guardrail


@dataclass
class OutputGuardrailResult:
    passed: bool
    blocked: bool
    reasons: list[str] = field(default_factory=list)


class OutputGuardrailRunner:
    def __init__(self):
        self.toxicity = ToxicityDetector()
        self.topic = TopicEnforcer()
        self.pii = PIIScanner()

    @observe_guardrail(module="output_guardrail_runner", guardrail_type="output")
    def check(self, text: str, topic: str | None = None) -> OutputGuardrailResult:
        reasons: list[str] = []

        tox = self.toxicity.check(text)
        if tox.flagged:
            reasons.append(f"Toxic content detected (score={tox.score:.2f})")

        topic_result = self.topic.check(text, topic)
        if not topic_result.on_topic:
            reasons.extend(topic_result.off_topic_segments)

        pii_result = self.pii.scan(text)
        if pii_result.flagged:
            types = {f["type"] for f in pii_result.findings}
            reasons.append(f"PII detected: {', '.join(types)}")

        return OutputGuardrailResult(
            passed=len(reasons) == 0,
            blocked=len(reasons) > 0,
            reasons=reasons,
        )
