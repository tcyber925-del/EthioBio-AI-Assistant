import asyncio
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.intervention.learning_engine import InterventionLearningEngine
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

logger = structlog.get_logger()

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
        session: AsyncSession | None = None,
    ) -> list[LearningRecommendation]:
        results = await asyncio.gather(
            *(gen(snapshot) for gen in RULE_GENERATORS),
            return_exceptions=True,
        )

        readiness_results = await generate_readiness_recommendations(
            snapshot,
            readiness_profile,
        )
        results = [r for r in results if not isinstance(r, BaseException)]
        results.append(readiness_results)

        if session is not None:
            try:
                learner = InterventionLearningEngine(session)
                weak_topics: list[str] = list(
                    dict.fromkeys(
                        snapshot.weak_topics or [],
                    )
                )
                learned = await learner.get_boosted_recommendations(
                    user_id=user_id,
                    weak_topics=weak_topics,
                )
                if learned:
                    results.append(learned)
            except Exception:
                logger.warning("learning_engine_recommend_failed", exc_info=True)

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
