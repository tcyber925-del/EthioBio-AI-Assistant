"""TutorContextAdapter — orchestrates snapshot, profile, recommendations, strategy into one package."""  # noqa: E501

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.readiness import ReadinessService
from src.core.learning_intelligence.recommendation.services import RecommendationService
from src.core.learning_intelligence.snapshot.snapshot_service import SnapshotService
from src.core.learning_intelligence.tutor.adaptive_strategy_selector import (
    STRATEGY_INSTRUCTIONS,
    AdaptiveStrategySelector,
)
from src.core.learning_intelligence.tutor.learner_profile_builder import (
    LearnerProfileBuilder,
)
from src.core.learning_intelligence.tutor.tutor_context_package import (
    TutorContextPackage,
)


def format_context_block(
    profile_block: str,
    recommendations: list,
    strategy: str,
) -> str:
    lines = [profile_block]

    if recommendations:
        lines.append("")
        lines.append("## Learning Recommendations")
        for rec in recommendations:
            reason = rec.get("reason") if isinstance(rec, dict) else getattr(rec, "reason", "")
            if reason:
                lines.append(f"- {reason}")

    if strategy and strategy in STRATEGY_INSTRUCTIONS:
        lines.append("")
        lines.append(f"## Teaching Strategy: {strategy}")
        lines.append(STRATEGY_INSTRUCTIONS[strategy])

    return "\n".join(lines)


class TutorContextAdapter:
    def __init__(
        self,
        snapshot_service: Optional[SnapshotService] = None,
        profile_builder: Optional[LearnerProfileBuilder] = None,
        recommendation_service: Optional[RecommendationService] = None,
        strategy_selector: Optional[AdaptiveStrategySelector] = None,
        readiness_service: Optional[ReadinessService] = None,
    ):
        self._snapshot_service = snapshot_service or SnapshotService()
        self._profile_builder = profile_builder or LearnerProfileBuilder()
        self._recommendation_service = recommendation_service or RecommendationService()
        self._strategy_selector = strategy_selector or AdaptiveStrategySelector()
        self._readiness_service = readiness_service or ReadinessService()

    async def build(
        self,
        session: AsyncSession,
        user_id: UUID,
        current_topic: Optional[str] = None,
    ) -> TutorContextPackage:
        snapshot = await self._snapshot_service.get_snapshot(session, user_id)

        readiness_context = None
        try:
            readiness = await self._readiness_service.get_readiness(session, user_id)
            if readiness.risk_topics:
                readiness_context = {
                    "risk_topics": readiness.risk_topics,
                    "overall_readiness": readiness.overall_readiness,
                    "readiness_band": readiness.readiness_band,
                }
        except Exception:
            readiness_context = None

        profile = self._profile_builder.build_profile(
            snapshot,
            current_topic,
            readiness_context=readiness_context,
        )
        recommendations = await self._recommendation_service.get_recommendations(session, user_id)
        strategy = self._strategy_selector.select(
            profile,
            snapshot,
            recommendations,
            readiness_context=readiness_context,
            current_topic=current_topic,
        )
        formatted_block = format_context_block(
            profile_block=profile.profile_block,
            recommendations=recommendations[:3],
            strategy=strategy,
        )
        return TutorContextPackage(
            learner_snapshot=snapshot,
            profile_block=profile.profile_block,
            difficulty_level=profile.difficulty_level,
            known_misconceptions=profile.known_misconceptions,
            top_recommendations=recommendations[:3],
            selected_strategy=strategy,
            formatted_block=formatted_block,
        )
