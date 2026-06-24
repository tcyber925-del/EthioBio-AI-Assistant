import structlog

MISCONCEPTION_INDICATORS = [
    "that's not quite right",
    "that's not correct",
    "that is incorrect",
    "i see a misconception",
    "common misconception",
    "you're confusing",
    "you are confusing",
    "that's a misunderstanding",
    "there's a misunderstanding",
    "this is a common error",
    "a common mistake",
    "this is incorrect",
    "that is wrong",
    "that's wrong",
    "not accurate",
    "this isn't correct",
    "that isn't correct",
    "i think there's a misunderstanding",
    "i think there is a misunderstanding",
]

logger = structlog.get_logger()


class HeuristicDetector:
    def detect_in_text(self, text: str) -> tuple[bool, str]:
        text_lower = text.lower()
        for indicator in MISCONCEPTION_INDICATORS:
            if indicator in text_lower:
                correction = self._extract_correction(text, indicator)
                return True, correction
        return False, ""

    def _extract_correction(self, text: str, indicator: str) -> str:
        sentences = text.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|").split("|")
        for i, sentence in enumerate(sentences):
            if indicator in sentence.lower():
                combined = sentence
                if i + 1 < len(sentences):
                    combined += " " + sentences[i + 1]
                return combined[:300]
        return text[:300]
