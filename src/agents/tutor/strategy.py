import re

from src.agents.tutor.models import TeachingStrategy

CONCEPTUAL_KEYWORDS = [
    "why",
    "how",
    "explain",
    "compare",
    "contrast",
    "what is the difference",
    "what's the difference",
    "what is the relationship",
    "what's the relationship",
]


def select_teaching_strategy(
    user_message: str,
    socratic_mode: bool,
    hint_level: int,
    intent: str,
    misconception_detected: bool,
    learner_profile_block: str,
) -> TeachingStrategy:
    if socratic_mode or hint_level > 0:
        return TeachingStrategy.SOCRATIC

    if intent == "quiz":
        return TeachingStrategy.ASSESSMENT_PREP

    msg_lower = user_message.lower()
    if re.search(r"\b(?:exam|test|quiz|prepare|practice|assessment)\b", msg_lower):
        return TeachingStrategy.ASSESSMENT_PREP

    if misconception_detected or "weak_areas" in learner_profile_block.lower():
        return TeachingStrategy.REMEDIATION

    for kw in CONCEPTUAL_KEYWORDS:
        if kw in msg_lower:
            return TeachingStrategy.GUIDED_DISCOVERY

    return TeachingStrategy.DIRECT_EXPLANATION
