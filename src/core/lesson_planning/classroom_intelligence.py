from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.intervention.knowledge_base import InterventionKnowledgeBase
from src.core.learning_intelligence.teacher.teacher_service import (
    TeacherService,
)
from src.core.misconception_intelligence.profiler import (
    MisconceptionProfiler,
)
from src.database.models import (
    ClassEnrollment,
    CurriculumTopic,
    TopicPrerequisite,
)

logger = structlog.get_logger()


class ClassroomIntelligenceService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._teacher_service = TeacherService()
        self._misconception_profiler = MisconceptionProfiler()
        self._kb = InterventionKnowledgeBase()

    async def get_student_ids(self, classroom_id: UUID) -> list[UUID]:
        result = await self._session.execute(
            select(ClassEnrollment.student_id).where(
                ClassEnrollment.class_id == classroom_id,
            )
        )
        return [row[0] for row in result.all()]

    async def _get_topic_id(self, topic_name: str, grade_level: int | None = None) -> UUID | None:
        stmt = select(CurriculumTopic.id).where(CurriculumTopic.topic.ilike(topic_name))
        if grade_level is not None:
            stmt = stmt.where(CurriculumTopic.grade_level == grade_level)
        result = await self._session.execute(stmt.limit(1))
        row = result.scalar_one_or_none()
        return row

    async def _get_prerequisite_gaps(
        self,
        topic_name: str,
        student_ids: list[UUID],
    ) -> list[dict]:
        topic_id = await self._get_topic_id(topic_name)
        if not topic_id:
            return []

        prereq_result = await self._session.execute(
            select(TopicPrerequisite.prerequisite_topic_id).where(
                TopicPrerequisite.topic_id == topic_id,
            )
        )
        prereq_ids = [row[0] for row in prereq_result.all()]
        if not prereq_ids:
            return []

        prereq_result2 = await self._session.execute(
            select(CurriculumTopic.id, CurriculumTopic.topic).where(
                CurriculumTopic.id.in_(prereq_ids),
            )
        )
        prereq_topics = {row.id: row.topic for row in prereq_result2.all()}

        return [
            {
                "topic": prereq_name,
                "affected_count": 0,
                "total_checked": min(len(student_ids), 10),
            }
            for prereq_name in prereq_topics.values()
        ]

    async def analyze(
        self,
        classroom_id: UUID,
        topic: str | None = None,
    ) -> dict:
        classroom = await self._teacher_service.get_classroom_overview(
            self._session, classroom_id,
        )

        misconceptions = await self._misconception_profiler.get_classroom_heatmap(
            classroom_id, self._session,
        )

        student_ids = await self.get_student_ids(classroom_id)

        prerequisite_gaps: list[dict] = []
        best_strategies: list[dict] = []

        if topic:
            prerequisite_gaps = await self._get_prerequisite_gaps(
                topic, student_ids,
            )

            strategies = await self._kb.query(
                session=self._session,
                topic=topic,
                min_effectiveness=60.0,
            )
            seen_types: set[str] = set()
            for s in (strategies or []):
                stype = s.intervention_type
                if stype and stype not in seen_types:
                    seen_types.add(stype)
                    best_strategies.append({
                        "type": stype,
                        "avg_effectiveness": round(s.effectiveness_score, 1),
                    })

        return {
            "classroom_id": str(classroom_id),
            "classroom": {
                "total_students": classroom.total_students,
                "classroom_health": round(classroom.classroom_health, 1),
                "readiness_distribution": classroom.readiness_distribution,
                "risk_students": [
                    {
                        "student_id": str(r.student_id),
                        "readiness_score": r.readiness_score,
                        "risk_level": r.risk_level,
                        "risk_factors": r.risk_factors,
                    }
                    for r in classroom.risk_students
                ],
                "mastery_heatmap": classroom.mastery_heatmap,
            },
            "misconceptions": {
                "total_unresolved": misconceptions.get("total_unresolved_patterns", 0),
                "affected_students": misconceptions.get("students_with_misconceptions", 0),
                "by_topic": [
                    {
                        "topic": t.get("topic", ""),
                        "affected_students": t.get("affected_students", 0),
                        "impact_pct": round(t.get("impact_percentage", 0), 1),
                        "top_pattern": t.get("top_pattern", ""),
                    }
                    for t in (misconceptions.get("by_topic") or [])
                    if t.get("top_pattern")
                ],
            },
            "prerequisite_gaps": prerequisite_gaps,
            "best_strategies": best_strategies,
        }
