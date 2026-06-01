from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)


async def generate_recovery_recommendations(
    snapshot: LearnerSnapshot,
) -> list[LearningRecommendation]:
    recommendations: list[LearningRecommendation] = []
    for plan in snapshot.active_recovery_plans:
        score = 15
        if plan.progress_pct >= 80:
            score += 10
        difference = plan.total_tasks - plan.completed_tasks
        recommendations.append(
            LearningRecommendation(
                id="",
                action_type=LearningActionType.COMPLETE_RECOVERY_TASK,
                topic=plan.topic,
                priority_score=float(score),
                reason=(
                    f"Active recovery plan for {plan.topic} "
                    f"({difference} task{'s' if difference != 1 else ''} remaining)"
                ),
                explanation=(
                    f"You have {difference} unfinished recovery "
                    f"task{'s' if difference != 1 else ''} in {plan.topic}. "
                    f"Complete {'them' if difference != 1 else 'it'} "
                    "to stay on track."
                ),
                generated_at=snapshot.generated_at,
            )
        )
    return recommendations
