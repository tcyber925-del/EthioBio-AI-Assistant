from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)


async def generate_review_recommendations(
    snapshot: LearnerSnapshot,
) -> list[LearningRecommendation]:
    recommendations: list[LearningRecommendation] = []
    for review in snapshot.due_reviews:
        overdue = review.days_overdue
        if overdue >= 8:
            score = 30
            severity = "severely"
        elif overdue >= 4:
            score = 20
            severity = "moderately"
        else:
            score = 10
            severity = "slightly"

        recommendations.append(
            LearningRecommendation(
                id="",
                action_type=LearningActionType.REVIEW_TOPIC,
                topic=review.topic,
                priority_score=float(score),
                reason=(
                    f"Review of {review.topic} is {overdue} "
                    f"day{'s' if overdue != 1 else ''} overdue "
                    f"({severity} overdue)"
                ),
                explanation=(
                    f"Your review of {review.topic} is overdue by {overdue} "
                    f"day{'s' if overdue != 1 else ''}. "
                    "Spaced repetition works best when you review on time."
                ),
                generated_at=snapshot.generated_at,
            )
        )
    return recommendations
