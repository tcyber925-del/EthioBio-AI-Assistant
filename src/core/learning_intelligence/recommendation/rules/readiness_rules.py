from datetime import datetime, timezone

from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
)
from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)


async def generate_readiness_recommendations(
    snapshot: LearnerSnapshot,
    readiness_profile: ExamReadinessProfile | None = None,
) -> list[LearningRecommendation]:
    recommendations: list[LearningRecommendation] = []
    if readiness_profile is None:
        return recommendations

    risk_topics = readiness_profile.risk_topics
    readiness_by_topic = {
        tr.topic: tr.readiness_score
        for tr in readiness_profile.topic_readiness
    }

    now = snapshot.generated_at or datetime.now(timezone.utc)

    for topic in risk_topics:
        readiness_score = readiness_by_topic.get(topic, 50.0)
        raw_score = (100.0 - readiness_score) / 100.0 * 40.0

        recommendations.append(
            LearningRecommendation(
                id="",
                action_type=LearningActionType.REVIEW_TOPIC,
                topic=topic,
                priority_score=raw_score,
                reason=f"Exam risk topic — low readiness in {topic}",
                explanation=(
                    f"{topic} is flagged as a high-risk exam area "
                    f"(readiness: {readiness_score:.0f}%). "
                    "Prioritise review to improve exam readiness."
                ),
                generated_at=now,
            )
        )

    return recommendations
