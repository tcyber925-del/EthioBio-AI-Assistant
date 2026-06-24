from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.intervention.knowledge_base import InterventionKnowledgeBase
from src.core.learning_intelligence.readiness.models.intervention import Intervention
from src.database.models import (
    InterventionAssignment,
    InterventionKnowledgeEntry,
    MisconceptionPattern,
    StudentMastery,
)
from src.schemas.intervention import InterventionCreate, InterventionUpdate

logger = structlog.get_logger()

EFFECTIVENESS_WEIGHTS = {
    "mastery_change": 0.35,
    "readiness_change": 0.25,
    "retention_change": 0.20,
    "misconception_reduction": 0.20,
}


class InterventionService:
    async def create(
        self,
        data: InterventionCreate,
        session: AsyncSession,
    ) -> InterventionAssignment:
        record = InterventionAssignment(
            user_id=data.user_id,
            classroom_id=data.classroom_id,
            teacher_id=data.teacher_id,
            intervention_type=data.intervention_type,
            topic=data.topic,
            priority=data.priority,
            estimated_impact=data.estimated_impact,
            notes=data.notes,
        )
        session.add(record)
        await session.flush()
        logger.info("intervention_created", id=record.id, type=data.intervention_type)
        return record

    async def update(
        self,
        intervention_id: str,
        data: InterventionUpdate,
        session: AsyncSession,
    ) -> InterventionAssignment | None:
        record = await session.get(InterventionAssignment, intervention_id)
        if not record:
            return None

        if data.status is not None:
            record.status = data.status
            if data.status == "active" and record.started_at is None:
                record.started_at = datetime.now(timezone.utc)
            elif data.status == "completed":
                record.completed_at = datetime.now(timezone.utc)
            elif data.status == "cancelled":
                record.status = "cancelled"

        if data.effectiveness_score is not None:
            record.effectiveness_score = data.effectiveness_score
            record.status = "completed"
            record.completed_at = datetime.now(timezone.utc)

        if data.notes is not None:
            record.notes = data.notes

        await session.flush()
        logger.info("intervention_updated", id=intervention_id, status=record.status)
        return record

    async def get(
        self,
        intervention_id: str,
        session: AsyncSession,
    ) -> InterventionAssignment | None:
        return await session.get(InterventionAssignment, intervention_id)

    async def list_for_user(
        self,
        user_id: str,
        session: AsyncSession,
        status: str | None = None,
    ) -> list[InterventionAssignment]:
        stmt = select(InterventionAssignment).where(
            InterventionAssignment.user_id == user_id
        )
        if status:
            stmt = stmt.where(InterventionAssignment.status == status)
        stmt = stmt.order_by(InterventionAssignment.priority.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_classroom(
        self,
        classroom_id: str,
        session: AsyncSession,
        status: str | None = None,
    ) -> list[InterventionAssignment]:
        stmt = select(InterventionAssignment).where(
            InterventionAssignment.classroom_id == classroom_id
        )
        if status:
            stmt = stmt.where(InterventionAssignment.status == status)
        stmt = stmt.order_by(InterventionAssignment.priority.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def persist_planned(
        self,
        interventions: list[Intervention],
        user_id: str,
        session: AsyncSession,
        teacher_id: str | None = None,
    ) -> list[InterventionAssignment]:
        created: list[InterventionAssignment] = []
        for iv in interventions:
            record = InterventionAssignment(
                user_id=user_id,
                teacher_id=teacher_id,
                intervention_type=iv.action_type,
                topic=iv.topic,
                priority=iv.priority,
                estimated_impact=iv.estimated_impact,
                notes=iv.reason,
            )
            session.add(record)
            created.append(record)
        await session.flush()
        logger.info("interventions_persisted", count=len(created))
        return created

    async def compute_effectiveness(
        self,
        intervention_id: str,
        session: AsyncSession,
    ) -> float | None:
        result = await self.compute_weighted_effectiveness(intervention_id, session)
        if result is None:
            return None
        return result["total_score"]

    async def compute_weighted_effectiveness(
        self,
        intervention_id: str,
        session: AsyncSession,
    ) -> dict | None:
        record = await session.get(InterventionAssignment, intervention_id)
        if not record or not record.topic:
            return None

        mastery = await self._get_mastery_change(record, session)
        if mastery is None:
            logger.info("weighted_effectiveness_no_mastery_data", id=intervention_id)
            return None

        readiness = await self._get_readiness_change(record, session)
        retention = await self._get_retention_change(record, session)
        misconception = await self._get_misconception_reduction(record, session)

        total = (
            mastery * EFFECTIVENESS_WEIGHTS["mastery_change"]
            + readiness * EFFECTIVENESS_WEIGHTS["readiness_change"]
            + retention * EFFECTIVENESS_WEIGHTS["retention_change"]
            + misconception * EFFECTIVENESS_WEIGHTS["misconception_reduction"]
        )

        record.effectiveness_score = round(total, 1)
        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc)
        await session.flush()

        try:
            kb = InterventionKnowledgeBase()
            await kb.store(
                intervention=record,
                components={
                    "mastery_change": mastery,
                    "readiness_change": readiness,
                    "retention_change": retention,
                    "misconception_reduction": misconception,
                },
                session=session,
            )
        except Exception:
            logger.warning("intervention_kb_store_failed", id=intervention_id)

        logger.info(
            "weighted_effectiveness_computed",
            id=intervention_id,
            total=total,
            mastery=mastery,
            readiness=readiness,
            retention=retention,
            misconception=misconception,
        )

        confidence_data = await self._compute_confidence_score(record, session)

        return {
            "total_score": round(total, 1),
            "components": {
                "mastery_change": round(mastery, 1),
                "readiness_change": round(readiness, 1),
                "retention_change": round(retention, 1),
                "misconception_reduction": round(misconception, 1),
            },
            "confidence": confidence_data["confidence"],
            "sample_size": confidence_data["sample_size"],
        }

    async def _compute_confidence_score(
        self,
        record: InterventionAssignment,
        session: AsyncSession,
    ) -> dict:
        result = await session.execute(
            select(
                func.count(),
                func.stddev(InterventionKnowledgeEntry.effectiveness_score),
                func.avg(InterventionKnowledgeEntry.effectiveness_score),
            ).where(
                InterventionKnowledgeEntry.intervention_type == record.intervention_type,
                InterventionKnowledgeEntry.topic == record.topic,
            )
        )
        row = result.one_or_none()
        if row is None:
            return {"confidence": 0.5, "sample_size": 0}
        n = row[0] or 0
        stddev = row[1]
        avg = row[2]

        sample_factor = n / (n + 5)
        if stddev is not None and avg is not None and avg > 0:
            cv = stddev / max(avg, 5)
            consistency_factor = max(0.0, 1.0 - cv)
        else:
            consistency_factor = 0.5

        confidence = round(0.6 * sample_factor + 0.4 * consistency_factor, 3)
        return {"confidence": min(confidence, 1.0), "sample_size": n}

    async def _get_mastery_change(
        self, record: InterventionAssignment, session: AsyncSession,
    ) -> float | None:
        before = await session.execute(
            select(StudentMastery).where(
                StudentMastery.user_id == record.user_id,
                StudentMastery.topic == record.topic,
                StudentMastery.created_at < record.assigned_at,
            ).order_by(StudentMastery.created_at.desc()).limit(1)
        )
        before_rec = before.scalar_one_or_none()
        after = await session.execute(
            select(StudentMastery).where(
                StudentMastery.user_id == record.user_id,
                StudentMastery.topic == record.topic,
                StudentMastery.created_at > record.assigned_at,
            ).order_by(StudentMastery.created_at.desc()).limit(1)
        )
        after_rec = after.scalar_one_or_none()

        if before_rec and after_rec:
            return max(0.0, min(after_rec.average_score - before_rec.average_score, 100.0))
        return None

    async def _get_readiness_change(
        self, record: InterventionAssignment, session: AsyncSession,
    ) -> float:
        try:
            from sqlalchemy import text as sa_text
            before = await session.execute(
                sa_text(
                    "SELECT rr.readiness_score FROM readiness_results rr "
                    "JOIN student_mastery sm ON sm.user_id = rr.user_id AND sm.topic = rr.topic "
                    "WHERE rr.user_id = :uid AND rr.topic = :topic "
                    "AND sm.created_at < :assigned "
                    "ORDER BY sm.created_at DESC LIMIT 1"
                ),
                {"uid": record.user_id, "topic": record.topic, "assigned": record.assigned_at},
            )
            before_val = before.scalar()
            after = await session.execute(
                sa_text(
                    "SELECT rr.readiness_score FROM readiness_results rr "
                    "JOIN student_mastery sm ON sm.user_id = rr.user_id AND sm.topic = rr.topic "
                    "WHERE rr.user_id = :uid AND rr.topic = :topic "
                    "AND sm.created_at > :assigned "
                    "ORDER BY sm.created_at DESC LIMIT 1"
                ),
                {"uid": record.user_id, "topic": record.topic, "assigned": record.assigned_at},
            )
            after_val = after.scalar()
            if before_val is not None and after_val is not None:
                return max(0.0, min(after_val - before_val, 100.0))
        except Exception:
            logger.warning("readiness_change_unavailable", topic=record.topic)
        return 0.0

    async def _get_retention_change(
        self, record: InterventionAssignment, session: AsyncSession,
    ) -> float:
        try:
            from sqlalchemy import text as sa_text
            result = await session.execute(
                sa_text(
                    "SELECT "
                    "  AVG(CASE WHEN srs.created_at < :assigned"
                    "    THEN srs.stability ELSE NULL END) AS before_stab, "
                    "  AVG(CASE WHEN srs.created_at > :assigned"
                    "    THEN srs.stability ELSE NULL END) AS after_stab "
                    "FROM spaced_repetition_schedule srs "
                    "WHERE srs.user_id = :uid AND srs.topic = :topic"
                ),
                {"uid": record.user_id, "topic": record.topic, "assigned": record.assigned_at},
            )
            row = result.fetchone()
            before = row.before_stab if row else None
            after = row.after_stab if row else None
            if before is not None and after is not None and before > 0:
                improvement = ((after - before) / before) * 100
                return max(0.0, min(improvement, 100.0))
        except Exception:
            logger.warning("retention_change_unavailable", topic=record.topic)
        return 0.0

    async def _get_misconception_reduction(
        self, record: InterventionAssignment, session: AsyncSession,
    ) -> float:
        before_count = await session.execute(
            select(func.count(MisconceptionPattern.id)).where(
                MisconceptionPattern.user_id == record.user_id,
                MisconceptionPattern.topic == record.topic,
                MisconceptionPattern.resolved.is_(False),
                MisconceptionPattern.last_detected_at < record.assigned_at,
            )
        )
        before = before_count.scalar() or 0
        after_count = await session.execute(
            select(func.count(MisconceptionPattern.id)).where(
                MisconceptionPattern.user_id == record.user_id,
                MisconceptionPattern.topic == record.topic,
                MisconceptionPattern.resolved.is_(False),
                MisconceptionPattern.last_detected_at > record.assigned_at,
            )
        )
        after = after_count.scalar() or 0

        if before > 0:
            reduction = ((before - after) / before) * 100
            return max(0.0, min(reduction, 100.0))
        return 0.0

    async def get_analytics(
        self,
        session: AsyncSession,
        user_id: str | None = None,
        teacher_id: str | None = None,
    ) -> dict:
        stmt = select(InterventionAssignment)
        if user_id:
            stmt = stmt.where(InterventionAssignment.user_id == user_id)
        if teacher_id:
            stmt = stmt.where(InterventionAssignment.teacher_id == teacher_id)

        result = await session.execute(stmt)
        records = list(result.scalars().all())

        total = len(records)
        completed = [r for r in records if r.status == "completed"]
        active = [r for r in records if r.status == "active"]
        completion_rate = (len(completed) / total * 100) if total > 0 else 0.0

        effectiveness_by_type: dict[str, list[float]] = {}
        effectiveness_by_topic: dict[str, list[float]] = {}
        for r in completed:
            if r.effectiveness_score is not None:
                by_type = effectiveness_by_type.setdefault(r.intervention_type, [])
                by_type.append(r.effectiveness_score)
                if r.topic:
                    by_topic = effectiveness_by_topic.setdefault(r.topic, [])
                    by_topic.append(r.effectiveness_score)

        avg_effectiveness = (
            sum(
                r.effectiveness_score
                for r in completed
                if r.effectiveness_score is not None
            ) / len([r for r in completed if r.effectiveness_score is not None])
            if any(r.effectiveness_score is not None for r in completed)
            else 0.0
        )

        return {
            "total_interventions": total,
            "completed_count": len(completed),
            "active_count": len(active),
            "completion_rate": round(completion_rate, 1),
            "average_effectiveness": round(avg_effectiveness, 1),
            "effectiveness_by_type": {
                k: round(sum(v) / len(v), 1) for k, v in effectiveness_by_type.items()
            },
            "effectiveness_by_topic": {
                k: round(sum(v) / len(v), 1) for k, v in effectiveness_by_topic.items()
            },
            "effectiveness_weights": EFFECTIVENESS_WEIGHTS,
        }
