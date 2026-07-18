from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import InterventionAssignment, InterventionKnowledgeEntry, StudentMastery

logger = structlog.get_logger()


class InterventionKnowledgeBase:
    async def store(
        self,
        intervention: InterventionAssignment,
        components: dict | None = None,
        session: AsyncSession = None,
    ) -> InterventionKnowledgeEntry | None:
        if not intervention.topic:
            return None

        mastery_before = None
        mastery_after = None
        if intervention.topic:
            before = await session.execute(
                select(StudentMastery)
                .where(
                    StudentMastery.user_id == intervention.user_id,
                    StudentMastery.topic == intervention.topic,
                    StudentMastery.created_at < intervention.assigned_at,
                )
                .order_by(StudentMastery.created_at.desc())
                .limit(1)
            )
            before_rec = before.scalar_one_or_none()
            if before_rec:
                mastery_before = before_rec.average_score

            after = await session.execute(
                select(StudentMastery)
                .where(
                    StudentMastery.user_id == intervention.user_id,
                    StudentMastery.topic == intervention.topic,
                    StudentMastery.created_at > intervention.assigned_at,
                )
                .order_by(StudentMastery.created_at.desc())
                .limit(1)
            )
            after_rec = after.scalar_one_or_none()
            if after_rec:
                mastery_after = after_rec.average_score

        comp = components or {}
        completed_at = intervention.completed_at or datetime.now(timezone.utc)
        assigned_at = intervention.assigned_at

        completion_days = None
        if completed_at and assigned_at:
            delta = (completed_at - assigned_at).days
            completion_days = max(0, delta)

        entry = InterventionKnowledgeEntry(
            intervention_id=intervention.id,
            intervention_type=intervention.intervention_type,
            topic=intervention.topic,
            user_id=intervention.user_id,
            teacher_id=intervention.teacher_id,
            classroom_id=intervention.classroom_id,
            effectiveness_score=intervention.effectiveness_score or 0.0,
            mastery_change=comp.get("mastery_change"),
            readiness_change=comp.get("readiness_change"),
            retention_change=comp.get("retention_change"),
            misconception_reduction=comp.get("misconception_reduction"),
            pre_mastery_score=mastery_before,
            post_mastery_score=mastery_after,
            priority=intervention.priority,
            estimated_impact=intervention.estimated_impact,
            completion_days=completion_days,
            assigned_at=assigned_at,
            completed_at=completed_at,
        )
        session.add(entry)
        await session.flush()
        logger.info(
            "intervention_kb_stored",
            id=entry.id,
            intervention_type=intervention.intervention_type,
            topic=intervention.topic,
        )
        return entry

    async def query(
        self,
        session: AsyncSession,
        intervention_type: str | None = None,
        topic: str | None = None,
        min_effectiveness: float | None = None,
        max_results: int = 20,
    ) -> list[InterventionKnowledgeEntry]:
        stmt = select(InterventionKnowledgeEntry)
        if intervention_type:
            stmt = stmt.where(
                InterventionKnowledgeEntry.intervention_type == intervention_type,
            )
        if topic:
            stmt = stmt.where(InterventionKnowledgeEntry.topic == topic)
        if min_effectiveness is not None:
            stmt = stmt.where(
                InterventionKnowledgeEntry.effectiveness_score >= min_effectiveness,
            )
        stmt = stmt.order_by(
            InterventionKnowledgeEntry.created_at.desc(),
        ).limit(max_results)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_effectiveness_summary(
        self,
        session: AsyncSession,
    ) -> dict:
        rows = await self.query(session, max_results=500)
        if not rows:
            return {"total_entries": 0, "by_type": {}, "average_score": 0.0}

        by_type: dict[str, list[float]] = {}
        for r in rows:
            by_type.setdefault(r.intervention_type, []).append(r.effectiveness_score)

        return {
            "total_entries": len(rows),
            "average_score": round(
                sum(r.effectiveness_score for r in rows) / len(rows),
                1,
            ),
            "by_type": {k: round(sum(v) / len(v), 1) for k, v in by_type.items()},
        }
