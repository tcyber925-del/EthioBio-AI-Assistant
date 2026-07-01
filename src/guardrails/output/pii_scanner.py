import re
from dataclasses import dataclass, field

from src.config import settings
from src.observability.guardrail_instrumentation import observe_guardrail


@dataclass
class PIIScanResult:
    flagged: bool
    findings: list[dict] = field(default_factory=list)


PII_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "phone", "Phone number"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "email", "Email address"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "ssn", "Social Security Number"),
    (
        re.compile(r"\b(?:ETH|ET)\s?\d{6,10}\b", re.IGNORECASE),
        "ethiopian_id",
        "Ethiopian ID number",
    ),
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b"), "credit_card", "Credit card number"),
    (re.compile(r"(?:\b0|\+251)\d{9}\b"), "ethiopian_phone", "Ethiopian phone number"),
]


class PIIScanner:
    def __init__(self):
        self._enabled = settings.output_pii_detection_enabled

    @observe_guardrail(module="pii_scanner", guardrail_type="output")
    def scan(self, text: str) -> PIIScanResult:
        if not self._enabled:
            return PIIScanResult(flagged=False)

        findings: list[dict] = []

        for pattern, pii_type, description in PII_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                findings.append(
                    {
                        "type": pii_type,
                        "description": description,
                        "match": match,
                        "position": text.index(match),
                    }
                )

        return PIIScanResult(flagged=len(findings) > 0, findings=findings)
