import asyncio
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.learning_intelligence.readiness.models import (
    ExamReadinessProfile,
)
from src.core.learning_intelligence.readiness.readiness_service import (
    ReadinessService,
)
from src.core.learning_intelligence.teacher.models import (
    ClassroomProfile,
    StudentRisk,
)
from src.database.models import ClassGroup

logger = structlog.get_logger()

RISK_READINESS_THRESHOLD = 40.0


class TeacherService:
    def __init__(
        self,
        readiness_service: ReadinessService | None = None,
    ):
        self._readiness_service = readiness_service or ReadinessService()

    async def get_classroom_overview(
        self,
        session: AsyncSession,
        classroom_id: UUID,
    ) -> ClassroomProfile:
        class_group = await self._load_classroom(session, classroom_id)
        if not class_group:
            return self._empty_profile(classroom_id)

        students = class_group.students
        if not students:
            return self._empty_profile(classroom_id)

        profiles = await self._fetch_readiness_profiles(session, [s.id for s in students])

        return self._build_classroom_profile(
            classroom_id=classroom_id,
            student_count=len(students),
            profiles=profiles,
        )

    async def _load_classroom(
        self,
        session: AsyncSession,
        classroom_id: UUID,
    ) -> ClassGroup | None:
        result = await session.execute(
            select(ClassGroup)
            .where(ClassGroup.id == classroom_id)
            .options(selectinload(ClassGroup.students))
        )
        return result.scalar_one_or_none()

    async def _fetch_readiness_profiles(
        self,
        session: AsyncSession,
        student_ids: list[UUID],
    ) -> list[ExamReadinessProfile]:
        tasks = [self._safe_fetch_readiness(session, sid) for sid in student_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        profiles: list[ExamReadinessProfile] = []
        for r in results:
            if isinstance(r, ExamReadinessProfile):
                profiles.append(r)
            elif isinstance(r, Exception):
                logger.warning("readiness_fetch_failed", error=str(r))
        return profiles

    async def _safe_fetch_readiness(
        self,
        session: AsyncSession,
        student_id: UUID,
    ) -> ExamReadinessProfile | None:
        try:
            return await self._readiness_service.get_readiness(session, student_id)
        except Exception as e:
            logger.warning(
                "readiness_fetch_failed_for_student",
                student_id=str(student_id),
                error=str(e),
            )
            return None

    def _build_classroom_profile(
        self,
        classroom_id: UUID,
        student_count: int,
        profiles: list[ExamReadinessProfile],
    ) -> ClassroomProfile:
        now = datetime.now(timezone.utc)

        if not profiles:
            return self._empty_profile(classroom_id)

        readiness_scores = [p.overall_readiness for p in profiles]
        classroom_health = (
            sum(readiness_scores) / len(readiness_scores) if readiness_scores else 0.0
        )

        distribution: dict[str, int] = {
            "Critical": 0,
            "Developing": 0,
            "Ready": 0,
            "Strong": 0,
        }
        risk_students: list[StudentRisk] = []
        all_interventions: list = []
        topic_scores: dict[str, list[float]] = {}

        for profile in profiles:
            band = profile.readiness_band
            if band in distribution:
                distribution[band] += 1

            if profile.overall_readiness < RISK_READINESS_THRESHOLD:
                risk_students.append(
                    StudentRisk(
                        student_id=profile.user_id,
                        readiness_score=profile.overall_readiness,
                        risk_level=band.upper(),
                        risk_factors=["low_readiness"],
                        recommended_action="assign_recovery",
                    )
                )
            elif profile.risk_topics:
                risk_students.append(
                    StudentRisk(
                        student_id=profile.user_id,
                        readiness_score=profile.overall_readiness,
                        risk_level="MODERATE",
                        risk_factors=[f"risk_topic:{t}" for t in profile.risk_topics],
                        recommended_action="target_weak_topics",
                    )
                )

            all_interventions.extend(profile.recommended_interventions)

            for tr in profile.topic_readiness:
                topic = tr.topic
                if topic not in topic_scores:
                    topic_scores[topic] = []
                topic_scores[topic].append(tr.readiness_score)

        all_interventions.sort(key=lambda i: i.priority, reverse=True)

        mastery_heatmap = {
            topic: sum(scores) / len(scores) for topic, scores in topic_scores.items()
        }

        return ClassroomProfile(
            classroom_id=classroom_id,
            generated_at=now,
            total_students=student_count,
            classroom_health=round(classroom_health, 1),
            readiness_distribution=distribution,
            risk_students=risk_students,
            intervention_candidates=all_interventions,
            mastery_heatmap=mastery_heatmap,
        )

    def _empty_profile(self, classroom_id: UUID) -> ClassroomProfile:
        now = datetime.now(timezone.utc)
        return ClassroomProfile(
            classroom_id=classroom_id,
            generated_at=now,
            total_students=0,
            classroom_health=0.0,
            readiness_distribution={
                "Critical": 0,
                "Developing": 0,
                "Ready": 0,
                "Strong": 0,
            },
            risk_students=[],
            intervention_candidates=[],
            mastery_heatmap={},
        )
