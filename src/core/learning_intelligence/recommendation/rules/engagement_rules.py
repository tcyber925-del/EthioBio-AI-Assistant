from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)


async def generate_engagement_recommendations(
    snapshot: LearnerSnapshot,
) -> list[LearningRecommendation]:
    recommendations: list[LearningRecommendation] = []
    gamification = snapshot.gamification

    if gamification.current_streak <= 1:
        recommendations.append(
            LearningRecommendation(
                id="",
                action_type=LearningActionType.MAINTAIN_STREAK,
                topic=None,
                priority_score=10.0,
                reason="Learning streak is at risk of breaking",
                explanation=(
                    "Your current streak is very short or inactive. "
                    "Studying today will help build consistency."
                ),
                generated_at=snapshot.generated_at,
            )
        )

    if gamification.recent_activity_score < 0.3:
        recommendations.append(
            LearningRecommendation(
                id="",
                action_type=LearningActionType.MAINTAIN_STREAK,
                topic=None,
                priority_score=15.0,
                reason="Low recent activity level",
                explanation=(
                    "You have been less active recently. "
                    "Try to re-engage with your studies to maintain progress."
                ),
                generated_at=snapshot.generated_at,
            )
        )

    return recommendations
