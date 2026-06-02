from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.models import LearnerSnapshot
from src.core.learning_intelligence.readiness.forgetting_risk import (
    ForgettingRiskPredictor,
)
from src.core.learning_intelligence.readiness.intervention_planner import (
    InterventionPlanner,
)
from src.core.learning_intelligence.readiness.mastery_stability import (
    MasteryStabilityPredictor,
)
from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
    TopicReadiness,
)
from src.core.learning_intelligence.readiness.projected_score import (
    ProjectedScoreCalculator,
)
from src.core.learning_intelligence.snapshot.snapshot_service import (
    SnapshotService,
)


class ReadinessService:
    def __init__(
        self,
        snapshot_service: SnapshotService | None = None,
        forgetting_predictor: ForgettingRiskPredictor | None = None,
        stability_predictor: MasteryStabilityPredictor | None = None,
        score_calculator: ProjectedScoreCalculator | None = None,
        intervention_planner: InterventionPlanner | None = None,
    ):
        self._snapshot_service = snapshot_service or SnapshotService()
        self._forgetting_predictor = forgetting_predictor or ForgettingRiskPredictor()
        self._stability_predictor = stability_predictor or MasteryStabilityPredictor()
        self._score_calculator = score_calculator or ProjectedScoreCalculator()
        self._intervention_planner = intervention_planner or InterventionPlanner()

    async def get_readiness(
        self,
        session: AsyncSession,
        user_id: UUID,
    ) -> ExamReadinessProfile:
        snapshot = await self._snapshot_service.get_snapshot(session, user_id)
        return self._compute_readiness(snapshot, user_id)

    def _compute_readiness(
        self,
        snapshot: LearnerSnapshot,
        user_id: UUID,
    ) -> ExamReadinessProfile:
        mastery = snapshot.mastery_by_topic
        if not mastery:
            return ExamReadinessProfile(
                user_id=user_id,
                generated_at=snapshot.generated_at,
                overall_readiness=0.0,
                readiness_band="Critical",
                topic_readiness=[],
                risk_topics=[],
            )

        now = datetime.now(timezone.utc)
        topic_readiness_list: list[TopicReadiness] = []
        all_risk_topics: list[str] = []

        for topic, mastery_data in mastery.items():
            readiness_score = float(mastery_data.get("average_score", 50))
            risk_factors: list[str] = []

            for review in snapshot.due_reviews:
                if review.topic == topic and review.next_review_at < now:
                    risk_factors.append("overdue_review")
                    break

            for mc in snapshot.misconceptions:
                if mc.topic == topic and mc.frequency >= 3:
                    risk_factors.append("active_misconception")
                    break

            ability_data = snapshot.ability_by_topic.get(topic, {})
            ability_score = ability_data.get("ability_score", 0.5)
            uncertainty = ability_data.get("uncertainty", 0.0)
            if ability_score < 0.3 or uncertainty > 2.0:
                risk_factors.append("low_ability")

            factor_count = len(risk_factors)
            if factor_count >= 3:
                risk_level = "CRITICAL"
            elif factor_count == 2:
                risk_level = "HIGH"
            elif factor_count == 1:
                risk_level = "MODERATE"
            else:
                risk_level = "LOW"

            review_status = "overdue" if "overdue_review" in risk_factors else "current"

            tr = TopicReadiness(
                topic=topic,
                readiness_score=readiness_score,
                risk_level=risk_level,
                risk_factors=risk_factors,
                review_status=review_status,
            )
            topic_readiness_list.append(tr)

            if risk_level in ("HIGH", "CRITICAL"):
                all_risk_topics.append(topic)

        if topic_readiness_list:
            overall_readiness = sum(
                tr.readiness_score for tr in topic_readiness_list
            ) / len(topic_readiness_list)
        else:
            overall_readiness = 0.0

        if overall_readiness >= 80:
            readiness_band = "Strong"
        elif overall_readiness >= 60:
            readiness_band = "Ready"
        elif overall_readiness >= 40:
            readiness_band = "Developing"
        else:
            readiness_band = "Critical"

        profile = ExamReadinessProfile(
            user_id=user_id,
            generated_at=snapshot.generated_at,
            overall_readiness=overall_readiness,
            readiness_band=readiness_band,
            topic_readiness=topic_readiness_list,
            risk_topics=all_risk_topics,
        )

        forgetting_risks = self._forgetting_predictor.predict_forgetting(snapshot)
        stabilities = self._stability_predictor.predict_stability(snapshot)

        for tr in topic_readiness_list:
            if tr.topic in forgetting_risks:
                tr.forgetting_risk = forgetting_risks[tr.topic].forgetting_risk

        projected_score, confidence = self._score_calculator.calculate(
            profile, forgetting_risks, stabilities, snapshot,
        )
        interventions = self._intervention_planner.plan(
            snapshot, profile, forgetting_risks, stabilities,
        )

        profile.projected_exam_score = projected_score
        profile.confidence_score = confidence
        profile.recommended_interventions = interventions
        return profile
