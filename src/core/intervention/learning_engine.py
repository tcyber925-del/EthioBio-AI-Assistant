from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)
from src.database.models import InterventionKnowledgeEntry

logger = structlog.get_logger()

BOOST_WEIGHTS: dict[str, float] = {
    "REVIEW_TOPIC": 0.15,
    "REVISE_MISCONCEPTION": 0.20,
    "RECOVERY_PLAN": 0.15,
    "TAKE_QUIZ": 0.10,
    "EXAM_PRACTICE": 0.10,
    "TUTOR_SESSION": 0.15,
    "ENGAGEMENT_BOOST": 0.05,
}

TYPE_TO_ACTION: dict[str, LearningActionType] = {
    "REVIEW_TOPIC": LearningActionType.REVIEW_TOPIC,
    "REVISE_MISCONCEPTION": LearningActionType.REVISE_MISCONCEPTION,
    "RECOVERY_PLAN": LearningActionType.COMPLETE_RECOVERY_TASK,
    "TAKE_QUIZ": LearningActionType.TAKE_QUIZ,
    "EXAM_PRACTICE": LearningActionType.EXAM_PRACTICE,
    "TUTOR_SESSION": LearningActionType.ASK_TUTOR,
    "ENGAGEMENT_BOOST": LearningActionType.MAINTAIN_STREAK,
}


class InterventionLearningEngine:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_effectiveness_by_type(self) -> dict[str, float]:
        result = await self._session.execute(
            select(
                InterventionKnowledgeEntry.intervention_type,
                func.avg(InterventionKnowledgeEntry.effectiveness_score),
            ).group_by(InterventionKnowledgeEntry.intervention_type)
        )
        rows = result.fetchall()
        return {r.intervention_type: round(float(r[1]), 1) for r in rows if r[1] is not None}

    async def get_effectiveness_by_type_and_topic(
        self,
        topic: str,
    ) -> dict[str, float]:
        result = await self._session.execute(
            select(
                InterventionKnowledgeEntry.intervention_type,
                func.avg(InterventionKnowledgeEntry.effectiveness_score),
            )
            .where(InterventionKnowledgeEntry.topic == topic)
            .group_by(InterventionKnowledgeEntry.intervention_type)
        )
        rows = result.fetchall()
        return {r.intervention_type: round(float(r[1]), 1) for r in rows if r[1] is not None}

    async def get_boosted_recommendations(
        self,
        user_id: UUID,
        weak_topics: list[str],
    ) -> list[LearningRecommendation]:
        type_scores = await self.get_effectiveness_by_type()
        if not type_scores:
            return []

        global_avg = sum(type_scores.values()) / len(type_scores)
        recs: list[LearningRecommendation] = []
        user_id_short = str(user_id)[:8]

        for i, topic in enumerate(weak_topics[:3]):
            topic_scores = await self.get_effectiveness_by_type_and_topic(topic)
            candidates = topic_scores if topic_scores else type_scores
            best_type = max(candidates, key=lambda k: candidates.get(k, 0))
            best_score = candidates.get(best_type, 0)

            boost = BOOST_WEIGHTS.get(best_type, 0.10) + (best_score - global_avg) / 100 * 0.1
            boost = max(0.0, min(0.5, boost))

            action = TYPE_TO_ACTION.get(best_type, LearningActionType.REVIEW_TOPIC)
            recs.append(
                LearningRecommendation(
                    id=f"learned_{user_id_short}_{i}",
                    action_type=action,
                    topic=topic,
                    priority_score=0.5 + boost,
                    reason=(
                        f"Historical effectiveness suggests {best_type} "
                        f"works well for this topic (avg {best_score:.0f}%)"
                    ),
                    explanation=(
                        f"Interventions of type {best_type} "
                        f"have shown {best_score:.0f}% average "
                        f"effectiveness for {topic}"
                    ),
                    generated_at=datetime.now(timezone.utc),
                    metadata={"learned_boost": round(boost, 3), "avg_effectiveness": best_score},
                )
            )

        return recs
