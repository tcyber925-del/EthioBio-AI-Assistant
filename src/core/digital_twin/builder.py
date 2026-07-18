from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    MemoryEducationalSummary,
    MemoryEvent,
    SpacedRepetitionSchedule,
    StudentAbility,
    StudentDigitalTwin,
    TopicMasteryHistory,
)

logger = structlog.get_logger()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class TwinBuilder:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def rebuild(self, user_id: UUID) -> StudentDigitalTwin:
        knowledge = await self._build_knowledge(user_id)
        mastery = await self._build_mastery(user_id)
        misconceptions = await self._build_misconceptions(user_id)
        retention = await self._build_retention(user_id)
        readiness = await self._build_readiness(user_id, mastery)
        intervention = await self._build_intervention(user_id)

        dims = [knowledge, mastery, misconceptions, retention, readiness, intervention]
        active_dimensions = sum(1 for d in dims if d and isinstance(d, dict))
        total_possible = len(dims)
        overall_health = (
            "healthy"
            if active_dimensions >= total_possible * 0.8
            else "attention"
            if active_dimensions >= total_possible * 0.5
            else "critical"
        )

        confidence = _compute_confidence(dims)
        now = _now()

        twin = await self.session.get(StudentDigitalTwin, user_id)
        if twin is None:
            twin = StudentDigitalTwin(user_id=user_id)
            self.session.add(twin)

        twin.knowledge_state = knowledge or {}
        twin.mastery_state = mastery or {}
        twin.misconception_state = misconceptions or {}
        twin.retention_state = retention or {}
        twin.readiness_state = readiness or {}
        twin.intervention_state = intervention or {}
        twin.overall_health = overall_health
        twin.confidence = confidence
        twin.last_built_at = now
        twin.updated_at = now

        await self.session.flush()
        logger.info(
            "twin_rebuilt", user_id=str(user_id), health=overall_health, confidence=confidence
        )
        return twin

    async def _build_knowledge(self, user_id: UUID) -> dict | None:
        result = await self.session.execute(
            select(StudentAbility).where(StudentAbility.user_id == user_id)
        )
        rows = result.scalars().all()
        if not rows:
            return None
        topics = {}
        total = 0.0
        for r in rows:
            topics[r.topic] = r.ability_score
            total += r.ability_score
        return {
            "overall": round(total / len(rows), 2) if rows else 0.0,
            "topics": {t: round(s, 2) for t, s in topics.items()},
            "total_attempts": sum(r.attempt_count for r in rows),
        }

    async def _build_mastery(self, user_id: UUID) -> dict | None:
        result = await self.session.execute(
            select(TopicMasteryHistory)
            .where(TopicMasteryHistory.user_id == user_id)
            .order_by(TopicMasteryHistory.topic, TopicMasteryHistory.recorded_at.desc())
        )
        rows = result.scalars().all()
        if not rows:
            return None
        topics: dict[str, list[float]] = {}
        for r in rows:
            topics.setdefault(r.topic, []).append(r.average_score)
        mastery = {}
        for topic, scores in topics.items():
            mastery[topic] = {
                "current": round(scores[0], 2) if scores else 0.0,
                "average": round(sum(scores) / len(scores), 2) if scores else 0.0,
                "data_points": len(scores),
            }
        overall = (
            round(sum(m["current"] for m in mastery.values()) / len(mastery), 2) if mastery else 0.0
        )
        return {"overall": overall, "topics": mastery}

    async def _build_misconceptions(self, user_id: UUID) -> dict | None:
        result = await self.session.execute(
            select(MemoryEducationalSummary)
            .where(MemoryEducationalSummary.user_id == user_id)
            .order_by(MemoryEducationalSummary.created_at.desc())
        )
        rows = result.scalars().all()
        total_misconceptions = 0
        topic_misconceptions: dict[str, list[str]] = {}
        for r in rows:
            if r.key_misconceptions:
                for mc in r.key_misconceptions:
                    topic = mc.get("topic", r.topic) if isinstance(mc, dict) else r.topic
                    topic_misconceptions.setdefault(topic, []).append(
                        mc.get("pattern", str(mc)) if isinstance(mc, dict) else str(mc)
                    )
                    total_misconceptions += 1
        if not total_misconceptions:
            return None
        return {
            "total_active": total_misconceptions,
            "total_resolved": 0,
            "topics": topic_misconceptions,
        }

    async def _build_retention(self, user_id: UUID) -> dict | None:
        result = await self.session.execute(
            select(SpacedRepetitionSchedule).where(SpacedRepetitionSchedule.user_id == user_id)
        )
        rows = result.scalars().all()
        if not rows:
            return None
        now = _now()
        topics: dict[str, dict[str, Any]] = {}
        high_risk = 0
        for r in rows:
            last = _naive(r.last_reviewed_at)
            days_since = (now - last).days if last else 999
            risk = "high" if days_since > 30 else "medium" if days_since > 14 else "low"
            if risk == "high":
                high_risk += 1
            topics[r.topic] = {
                "mastery": r.mastery_score,
                "interval_days": r.interval_days,
                "review_count": r.review_count,
                "days_since_review": days_since,
                "forgetting_risk": risk,
            }

        if topics:
            total = sum(float(t["mastery"]) for t in topics.values())
            overall = round(total / len(topics), 2)
        else:
            overall = 0.0

        return {
            "overall": overall,
            "topics": topics,
            "high_risk_count": high_risk,
        }

    async def _build_readiness(self, user_id: UUID, mastery: dict | None) -> dict | None:
        ability_result = await self.session.execute(
            select(StudentAbility).where(StudentAbility.user_id == user_id)
        )
        abilities = {r.topic: r.ability_score for r in ability_result.scalars().all()}
        if not abilities:
            return None

        mastery_topics = mastery.get("topics", {}) if mastery else {}
        topics = {}
        for topic, ability in abilities.items():
            m = mastery_topics.get(topic, {})
            score = ability * 0.6 + m.get("current", 0.5) * 0.4
            risk_level = "high" if score < 0.4 else "medium" if score < 0.7 else "low"
            topics[topic] = {
                "readiness_score": round(score, 2),
                "risk_level": risk_level,
            }
        overall = (
            round(sum(t["readiness_score"] for t in topics.values()) / len(topics), 2)
            if topics
            else 0.0
        )
        return {"overall": overall, "topics": topics}

    async def _build_intervention(self, user_id: UUID) -> dict | None:
        result = await self.session.execute(
            select(MemoryEvent)
            .where(
                MemoryEvent.user_id == user_id,
                MemoryEvent.event_type == "intervention",
            )
            .order_by(MemoryEvent.created_at.desc())
        )
        rows = result.scalars().all()
        if not rows:
            return None
        completed = sum(1 for r in rows if r.event_metadata.get("status") == "completed")
        return {
            "active_count": len(rows) - completed,
            "completed_count": completed,
            "total": len(rows),
        }


def _compute_confidence(dimensions: list[dict | None]) -> float:
    populated = sum(
        1
        for d in dimensions
        if d
        and isinstance(d, dict)
        and (d.get("topics") or d.get("total_attempts", 0) > 0 or d.get("total", 0) > 0)
    )
    total = len([d for d in dimensions if d is not None])
    return round(populated / total, 2) if total else 0.0
