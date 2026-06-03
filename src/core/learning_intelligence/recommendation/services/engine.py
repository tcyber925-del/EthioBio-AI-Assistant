import asyncio
from uuid import UUID

from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
)
from src.core.learning_intelligence.recommendation.models import (
    LearningRecommendation,
)
from src.core.learning_intelligence.recommendation.rules import (
    generate_engagement_recommendations,
    generate_mastery_recommendations,
    generate_misconception_recommendations,
    generate_readiness_recommendations,
    generate_recovery_recommendations,
    generate_review_recommendations,
)
from src.core.learning_intelligence.recommendation.scoring import (
    PriorityCalculator,
)

RULE_GENERATORS = [
    generate_mastery_recommendations,
    generate_recovery_recommendations,
    generate_review_recommendations,
    generate_misconception_recommendations,
    generate_engagement_recommendations,
]


class RecommendationEngine:
    async def generate(
        self,
        snapshot: LearnerSnapshot,
        user_id: UUID,
        readiness_profile: ExamReadinessProfile | None = None,
    ) -> list[LearningRecommendation]:
        results = await asyncio.gather(
            *(gen(snapshot) for gen in RULE_GENERATORS),
            return_exceptions=True,
        )

        readiness_results = await generate_readiness_recommendations(
            snapshot, readiness_profile,
        )
        results = [r for r in results if not isinstance(r, BaseException)]
        results.append(readiness_results)

        all_recs: list[LearningRecommendation] = []
        for result in results:
            if isinstance(result, BaseException):
                continue
            if isinstance(result, list):
                all_recs.extend(result)

        scored = PriorityCalculator.score_and_sort(all_recs)

        user_id_short = str(user_id)[:8]
        for i, rec in enumerate(scored):
            rec.id = f"rec_{user_id_short}_{i}"

        return scored
