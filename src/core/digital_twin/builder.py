from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    InterventionAssignment,
    MisconceptionPattern,
    SpacedRepetitionSchedule,
    StudentAbility,
    StudentDigitalTwin,
    StudentMastery,
    TopicPrerequisite,
)

logger = structlog.get_logger()


class TwinBuilder:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def gather_knowledge_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(StudentAbility).where(
                StudentAbility.user_id == user_id,
                StudentAbility.ability_score != 0.0,
            )
        )
        rows = result.scalars().all()
        if not rows:
            return {}

        topics = {}
        total = 0.0
        for row in rows:
            topics[row.topic] = {
                "score": round(row.ability_score, 2),
                "uncertainty": round(row.uncertainty, 2),
                "data_points": row.attempt_count,
                "last_updated": (
                    row.updated_at.isoformat() if row.updated_at else None
                ),
                "confidence": round(
                    min(row.attempt_count / 10, 1.0) * 0.5
                    + 0.5 * max(0, 1 - (row.uncertainty / 5)), 2
                ),
            }
            total += row.ability_score

        return {"overall": round(total / len(rows), 2), "topics": topics}

    async def gather_mastery_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(StudentMastery).where(StudentMastery.user_id == user_id)
        )
        rows = result.scalars().all()
        if not rows:
            return {}

        topics = {}
        total = 0.0
        for row in rows:
            topics[row.topic] = {
                "mastery_score": row.average_score,
                "level": row.severity,
                "data_points": row.attempt_count,
                "last_assessed": (
                    row.last_assessed_at.isoformat()
                    if row.last_assessed_at else None
                ),
            }
            total += row.average_score

        return {"overall": round(total / len(rows), 2), "topics": topics}

    async def gather_misconception_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(MisconceptionPattern).where(
                MisconceptionPattern.user_id == user_id,
            )
        )
        rows = result.scalars().all()
        active = [r for r in rows if not r.resolved]
        resolved = [r for r in rows if r.resolved]

        topics = {}
        for row in active:
            topic = row.topic
            if topic not in topics:
                topics[topic] = []
            topics[topic].append({
                "pattern": row.pattern_description,
                "severity": row.severity,
                "frequency": row.frequency,
                "active_since": (
                    row.first_detected_at.isoformat()
                    if row.first_detected_at else None
                ),
            })

        return {
            "total_active": len(active),
            "total_resolved": len(resolved),
            "topics": topics,
        }

    async def gather_retention_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(SpacedRepetitionSchedule).where(
                SpacedRepetitionSchedule.user_id == user_id,
            )
        )
        rows = result.scalars().all()
        if not rows:
            return {}

        topics = {}
        total = 0.0
        for row in rows:
            days_since = None
            forgetting_risk = "unknown"
            if row.last_reviewed_at:
                delta_result = await self.session.execute(
                    select(func.extract("epoch", func.now() - row.last_reviewed_at) / 86400)
                )
                days_since = round(delta_result.scalar() or 0)
                if days_since > 14:
                    forgetting_risk = "high"
                elif days_since > 7:
                    forgetting_risk = "medium"
                else:
                    forgetting_risk = "low"

            topics[row.topic] = {
                "retention_score": row.mastery_score,
                "last_reviewed": (
                    row.last_reviewed_at.isoformat()
                    if row.last_reviewed_at else None
                ),
                "days_since_review": days_since,
                "forgetting_risk": forgetting_risk,
                "next_review": (
                    row.next_review_at.isoformat()
                    if row.next_review_at else None
                ),
            }
            total += row.mastery_score

        return {"overall": round(total / len(rows), 2), "topics": topics}

    async def gather_readiness_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(StudentMastery).where(
                StudentMastery.user_id == user_id,
            )
        )
        rows = result.scalars().all()
        if not rows:
            return {}

        topics = {}
        total = 0.0
        for row in rows:
            risk = "low"
            if row.average_score < 0.4:
                risk = "high"
            elif row.average_score < 0.6:
                risk = "medium"

            topics[row.topic] = {
                "readiness_score": row.average_score,
                "prerequisites_met": True,
                "risk_level": risk,
            }
            total += row.average_score

        return {"overall": round(total / len(rows), 2), "topics": topics}

    async def gather_intervention_state(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(InterventionAssignment).where(
                InterventionAssignment.user_id == user_id,
            )
        )
        rows = result.scalars().all()

        active = [r for r in rows if r.status == "active"]
        completed = [r for r in rows if r.status == "completed"]
        by_type: dict = {}
        for row in rows:
            t = row.intervention_type
            if t not in by_type:
                by_type[t] = {"assigned": 0, "completed": 0, "avg_effectiveness": 0.0}
            by_type[t]["assigned"] += 1
            if row.status == "completed" and row.effectiveness_score is not None:
                c = by_type[t]
                old_total = c["avg_effectiveness"] * c["completed"]
                c["completed"] += 1
                c["avg_effectiveness"] = round(
                    (old_total + row.effectiveness_score) / c["completed"], 2
                )

        effectiveness_scores = [
            r.effectiveness_score for r in completed
            if r.effectiveness_score is not None
        ]
        responsiveness = (
            round(sum(effectiveness_scores) / len(effectiveness_scores), 2)
            if effectiveness_scores else 0.0
        )

        return {
            "active_count": len(active),
            "completed_count": len(completed),
            "responsiveness": responsiveness,
            "by_type": by_type,
        }

    async def rebuild(self, user_id: UUID) -> dict:
        state = {
            "knowledge_state": await self.gather_knowledge_state(user_id),
            "mastery_state": await self.gather_mastery_state(user_id),
            "misconception_state": await self.gather_misconception_state(user_id),
            "retention_state": await self.gather_retention_state(user_id),
            "readiness_state": await self.gather_readiness_state(user_id),
            "intervention_state": await self.gather_intervention_state(user_id),
        }
        state["overall_health"] = self._compute_health(state)
        state["confidence"] = self._compute_confidence(state)

        existing = await self.session.get(StudentDigitalTwin, user_id)
        if existing:
            for key, val in state.items():
                setattr(existing, key, val)
            existing.last_built_at = func.now()
        else:
            self.session.add(StudentDigitalTwin(
                user_id=user_id, **state, last_built_at=func.now(),
            ))
        await self.session.commit()
        return state

    def _compute_health(self, state: dict) -> str:
        scores = []
        for dim_key in ("knowledge_state", "mastery_state", "retention_state", "readiness_state"):
            dim = state.get(dim_key, {})
            if dim and "overall" in dim:
                scores.append(dim["overall"])
        if not scores:
            return "unknown"
        avg = sum(scores) / len(scores)
        if avg >= 0.7:
            return "healthy"
        if avg >= 0.4:
            return "needs_attention"
        return "at_risk"

    def _compute_confidence(self, state: dict) -> float:
        dimensions = [
            "knowledge_state", "mastery_state", "misconception_state",
            "retention_state", "readiness_state", "intervention_state",
        ]
        scores = []
        for dim_name in dimensions:
            val = state.get(dim_name, {})
            if not val:
                continue
            if dim_name == "misconception_state":
                data_points = val.get("total_active", 0) + val.get("total_resolved", 0)
            elif dim_name == "intervention_state":
                data_points = val.get("active_count", 0) + val.get("completed_count", 0)
            else:
                topics = val.get("topics", {})
                if not topics:
                    continue
                data_points = sum(
                    t.get("data_points", 0) for t in topics.values()
                    if isinstance(t, dict)
                )
            freshness = 0.5
            volume = min(data_points / 10, 1.0)
            scores.append((0.5 * freshness) + (0.5 * volume))
        return round(sum(scores) / len(scores), 2) if scores else 0.0
