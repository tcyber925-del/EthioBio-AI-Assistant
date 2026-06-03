from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.gamification import XP_SOURCES
from src.core.learning_intelligence.models import (
    ContinueLearningFeed,
    FeedSummary,
    LearningCard,
)
from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
)
from src.core.learning_intelligence.recommendation.models import (
    LearningActionType,
    LearningRecommendation,
)
from src.core.learning_intelligence.recommendation.services import (
    RecommendationService,
)

ACTIVITY_DURATION_LOOKUP: dict[LearningActionType, int] = {
    LearningActionType.REVIEW_TOPIC: 10,
    LearningActionType.TAKE_QUIZ: 15,
    LearningActionType.COMPLETE_RECOVERY_TASK: 10,
    LearningActionType.REVISE_MISCONCEPTION: 15,
    LearningActionType.STUDY_DIAGRAM: 10,
    LearningActionType.READ_CONTENT: 15,
    LearningActionType.ASK_TUTOR: 10,
    LearningActionType.EXAM_PRACTICE: 20,
    LearningActionType.MAINTAIN_STREAK: 5,
}

ACTION_TYPE_TO_SECTION: dict[LearningActionType, str] = {
    LearningActionType.REVIEW_TOPIC: "review_actions",
    LearningActionType.TAKE_QUIZ: "quiz_opportunities",
    LearningActionType.COMPLETE_RECOVERY_TASK: "recovery_actions",
    LearningActionType.REVISE_MISCONCEPTION: "tutor_actions",
    LearningActionType.STUDY_DIAGRAM: "review_actions",
    LearningActionType.READ_CONTENT: "review_actions",
    LearningActionType.ASK_TUTOR: "tutor_actions",
    LearningActionType.EXAM_PRACTICE: "quiz_opportunities",
    LearningActionType.MAINTAIN_STREAK: "tutor_actions",
}

ACTION_TYPE_TO_XP_SOURCE_KEY: dict[LearningActionType, str] = {
    LearningActionType.REVIEW_TOPIC: "tutor_interaction",
    LearningActionType.TAKE_QUIZ: "quiz_completion",
    LearningActionType.COMPLETE_RECOVERY_TASK: "recovery_task_completion",
    LearningActionType.REVISE_MISCONCEPTION: "tutor_interaction",
    LearningActionType.STUDY_DIAGRAM: "tutor_interaction",
    LearningActionType.READ_CONTENT: "tutor_interaction",
    LearningActionType.ASK_TUTOR: "tutor_interaction",
    LearningActionType.EXAM_PRACTICE: "quiz_completion",
    LearningActionType.MAINTAIN_STREAK: "daily_streak_bonus",
}


def _recommendation_to_card(
    rec: LearningRecommendation,
) -> LearningCard:
    estimated = ACTIVITY_DURATION_LOOKUP.get(rec.action_type, 10)
    xp_key = ACTION_TYPE_TO_XP_SOURCE_KEY.get(rec.action_type)
    xp = XP_SOURCES.get(xp_key) if xp_key else None
    return LearningCard(
        id=rec.id,
        title=rec.reason or rec.action_type.value.replace("_", " ").title(),
        description=rec.explanation,
        action_type=rec.action_type,
        priority_score=rec.priority_score,
        estimated_minutes=estimated,
        xp_reward=xp,
        topic=rec.topic,
        metadata=rec.metadata,
    )


SECTION_ORDER = [
    "recovery_actions",
    "review_actions",
    "quiz_opportunities",
    "tutor_actions",
]


class ContinueLearningService:
    def __init__(
        self,
        recommendation_service: RecommendationService | None = None,
    ):
        self._recommendation_service = (
            recommendation_service or RecommendationService()
        )

    async def get_feed(
        self,
        session: AsyncSession,
        user_id: UUID,
        readiness_profile: ExamReadinessProfile | None = None,
    ) -> ContinueLearningFeed:
        recommendations = await self._recommendation_service.get_recommendations(
            session, user_id
        )

        if not recommendations:
            return self._empty_feed(user_id)

        sections: dict[str, list[LearningCard]] = {
            name: [] for name in SECTION_ORDER
        }

        cards = [_recommendation_to_card(r) for r in recommendations]

        if readiness_profile:
            self._apply_readiness_boost(cards, readiness_profile)

        for card in cards:
            section = ACTION_TYPE_TO_SECTION.get(card.action_type)
            if section and section in sections:
                sections[section].append(card)

        all_cards = [c for s in SECTION_ORDER for c in sections.get(s, [])]
        primary_action = all_cards[0] if all_cards else None

        total_minutes = sum(c.estimated_minutes for c in all_cards)
        total_xp = sum(c.xp_reward or 0 for c in all_cards)

        return ContinueLearningFeed(
            user_id=user_id,
            generated_at=datetime.now(timezone.utc),
            primary_action=primary_action,
            sections={k: v for k, v in sections.items() if v},
            summary=FeedSummary(
                estimated_minutes=total_minutes,
                xp_available=total_xp,
            ),
        )

    @staticmethod
    def _apply_readiness_boost(
        cards: list[LearningCard],
        readiness_profile: ExamReadinessProfile,
    ) -> None:
        risk_set = set(readiness_profile.risk_topics)
        for card in cards:
            if card.topic and card.topic in risk_set:
                card.priority_score = min(card.priority_score * 1.3, 100.0)
                card.exam_impact = "high"
        cards.sort(key=lambda c: c.priority_score, reverse=True)

    def _empty_feed(self, user_id: UUID) -> ContinueLearningFeed:
        now = datetime.now(timezone.utc)
        start_card = LearningCard(
            id="empty_start_quiz",
            title="Start with a Quiz",
            description="Take a quiz to assess your knowledge and unlock personalized learning.",
            action_type=LearningActionType.TAKE_QUIZ,
            priority_score=100.0,
            estimated_minutes=ACTIVITY_DURATION_LOOKUP.get(
                LearningActionType.TAKE_QUIZ, 15
            ),
            xp_reward=XP_SOURCES.get("quiz_completion", 10),
        )
        tutor_card = LearningCard(
            id="empty_ask_tutor",
            title="Ask the Tutor",
            description="Have a question? Ask our AI tutor for help with any biology topic.",
            action_type=LearningActionType.ASK_TUTOR,
            priority_score=50.0,
            estimated_minutes=ACTIVITY_DURATION_LOOKUP.get(
                LearningActionType.ASK_TUTOR, 10
            ),
            xp_reward=XP_SOURCES.get("tutor_interaction", 5),
        )
        return ContinueLearningFeed(
            user_id=user_id,
            generated_at=now,
            primary_action=start_card,
            sections={"quiz_opportunities": [start_card, tutor_card]},
            summary=FeedSummary(
                estimated_minutes=start_card.estimated_minutes
                + tutor_card.estimated_minutes,
                xp_available=(start_card.xp_reward or 0)
                + (tutor_card.xp_reward or 0),
            ),
        )
