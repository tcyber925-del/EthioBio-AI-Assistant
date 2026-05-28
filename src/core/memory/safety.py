import re

import structlog

logger = structlog.get_logger()

MAX_CONTENT_LENGTH = 2000
MIN_CONTENT_LENGTH = 10

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-()]{7,15}")
ETHIOPIA_PHONE_PATTERN = re.compile(r"\+251\d{9}|0\d{9}")


def sanitize_summary_content(text: str) -> str:
    if not text:
        return ""

    cleaned = EMAIL_PATTERN.sub("[email]", text)
    cleaned = ETHIOPIA_PHONE_PATTERN.sub("[phone]", cleaned)
    cleaned = PHONE_PATTERN.sub("[phone]", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def validate_summary_content(text: str) -> tuple[bool, str]:
    if not text or len(text.strip()) < MIN_CONTENT_LENGTH:
        return False, "content too short"
    if len(text) > MAX_CONTENT_LENGTH * 2:
        return False, "content exceeds maximum length"
    return True, ""


def validate_understanding_level(level: str | None) -> str:
    valid = {"beginner", "intermediate", "advanced", "mastered"}
    if level and level.lower() in valid:
        return level.lower()
    return "beginner"


def validate_confidence(confidence: float) -> float:
    return max(0.0, min(1.0, confidence))
