from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)


async def generate_misconception_recommendations(
    snapshot: LearnerSnapshot,
) -> list[LearningRecommendation]:
    recommendations: list[LearningRecommendation] = []
    for mc in snapshot.misconceptions:
        if mc.frequency < 2:
            continue
        recommendations.append(
            LearningRecommendation(
                id="",
                action_type=LearningActionType.REVISE_MISCONCEPTION,
                topic=mc.topic,
                priority_score=20.0,
                reason=(
                    f"Recurring misconception in {mc.topic} "
                    f"(appeared {mc.frequency} times, type: {mc.pattern_type})"
                ),
                explanation=(
                    f"You have repeatedly shown a '{mc.pattern_type}' "
                    f"misconception in {mc.topic} ({mc.frequency} occurrences). "
                    "Targeted revision can help correct this."
                ),
                generated_at=snapshot.generated_at,
            )
        )
    return recommendations
