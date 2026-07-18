from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)


async def generate_mastery_recommendations(
    snapshot: LearnerSnapshot,
) -> list[LearningRecommendation]:
    recommendations: list[LearningRecommendation] = []
    for topic in snapshot.weak_topics:
        meta = snapshot.mastery_by_topic.get(topic, {})
        severity = meta.get("severity", "moderate")
        if severity == "critical":
            score = 40
            reason = f"Critical mastery gap in {topic}"
        else:
            score = 25
            reason = f"Moderate mastery gap in {topic}"
        recommendations.append(
            LearningRecommendation(
                id="",
                action_type=LearningActionType.REVIEW_TOPIC,
                topic=topic,
                priority_score=float(score),
                reason=reason,
                explanation=(
                    f"Your performance in {topic} indicates a {severity} weakness. "
                    "Focused review is recommended."
                ),
                generated_at=snapshot.generated_at,
            )
        )
    return recommendations
