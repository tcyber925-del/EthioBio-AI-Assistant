"""AdaptiveStrategySelector — picks a teaching strategy based on learner state."""

from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.recommendation.models import LearningActionType
from src.core.learning_intelligence.tutor.learner_profile_builder import BuildProfileResult

STRATEGY_INSTRUCTIONS = {
    "DIRECT_EXPLANATION": (
        "Provide clear, direct explanations with relevant examples. "
        "Focus on building understanding step by step."
    ),
    "MISCONCEPTION_REMEDIATION": (
        "The student has a known misconception. After explaining the correct concept, "
        "explicitly contrast it with their misconception and verify their understanding."
    ),
    "CONFIDENCE_BUILDING": (
        "The student has low confidence. Use encouraging language, acknowledge their progress, "
        "and break down concepts into small, manageable steps. Praise correct reasoning."
    ),
    "RECOVERY_SUPPORT": (
        "The student has active recovery plans. When relevant, relate new content to their "
        "recovery topics and encourage them to continue their remediation work."
    ),
    "EXAM_PREPARATION": (
        "The student is preparing for exams. Include exam-style reasoning, cross-topic "
        "connections, and practice-oriented explanations."
    ),
}


class AdaptiveStrategySelector:
    STRATEGY_INSTRUCTIONS = STRATEGY_INSTRUCTIONS

    def select(
        self,
        profile: BuildProfileResult,
        snapshot: LearnerSnapshot,
        recommendations: list,
        readiness_context: dict | None = None,
        current_topic: str | None = None,
    ) -> str:
        if profile.known_misconceptions:
            return "MISCONCEPTION_REMEDIATION"

        confidence = snapshot.educational_memory.confidence
        if confidence is not None and confidence < 0.3:
            return "CONFIDENCE_BUILDING"

        if snapshot.active_recovery_plans:
            return "RECOVERY_SUPPORT"

        if readiness_context and current_topic:
            risk_topics = readiness_context.get("risk_topics", [])
            if current_topic in risk_topics:
                return "EXAM_PREPARATION"

        for rec in recommendations:
            if rec.action_type == LearningActionType.EXAM_PRACTICE:
                return "EXAM_PREPARATION"

        return "DIRECT_EXPLANATION"
