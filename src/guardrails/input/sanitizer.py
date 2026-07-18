import re
import unicodedata

from src.config import settings
from src.observability.guardrail_instrumentation import observe_guardrail


class InputSanitizer:
    MAX_INPUT_LENGTH = settings.input_max_length

    CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    @observe_guardrail(module="input_sanitizer", guardrail_type="input")
    def sanitize(self, text: str) -> str:
        text = unicodedata.normalize("NFC", text)
        text = self.CONTROL_CHAR_RE.sub("", text)
        text = text.strip()
        if len(text) > self.MAX_INPUT_LENGTH:
            text = text[: self.MAX_INPUT_LENGTH]
        return text

    def validate_length(self, text: str) -> bool:
        return 0 < len(text) <= self.MAX_INPUT_LENGTH
