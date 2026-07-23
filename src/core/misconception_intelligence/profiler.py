from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.memory.event_logger import EventLogger
from src.core.misconception_intelligence.knowledge_base_data import MISCONCEPTION_SEVERITIES
from src.database.models import ClassEnrollment, MisconceptionPattern

logger = structlog.get_logger()
event_logger = EventLogger()


class MisconceptionProfile:
    def __init__(
        self,
        total_patterns: int = 0,
        unresolved_count: int = 0,
        by_topic: list[dict] | None = None,
        frequent_patterns: list[dict] | None = None,
        improvement_trend: str = "stable",
    ):
        self.total_patterns = total_patterns
        self.unresolved_count = unresolved_count
        self.by_topic = by_topic or []
        self.frequent_patterns = frequent_patterns or []
        self.improvement_trend = improvement_trend


class MisconceptionProfiler:
    async def get_student_profile(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> MisconceptionProfile:
        result = await db.execute(
            select(MisconceptionPattern)
            .where(
                MisconceptionPattern.user_id == user_id,
                MisconceptionPattern.resolved.is_(False),
            )
            .order_by(MisconceptionPattern.last_detected_at.desc())
        )
        patterns = list(result.scalars().all())

        unresolved_count = len(patterns)

        topic_map: dict[str, list[dict]] = {}
        for p in patterns:
            if p.topic not in topic_map:
                topic_map[p.topic] = []
            topic_map[p.topic].append(
                {
                    "id": str(p.id),
                    "pattern_type": p.pattern_type,
                    "description": p.pattern_description,
                    "severity": p.severity,
                    "confidence": p.confidence,
                    "frequency": p.frequency,
                    "common_wrong_answer": p.common_wrong_answer,
                    "last_detected_at": str(p.last_detected_at),
                }
            )

        by_topic = []
        for topic, patterns in topic_map.items():
            entry = {
                "topic": topic,
                "count": len(patterns),
                "patterns": patterns,
            }
            try:
                from src.core.misconception_intelligence import MisconceptionGraphIntegrator

                gi = MisconceptionGraphIntegrator()
                entry["prerequisite_gaps"] = await gi.get_prerequisite_gaps(
                    user_id=user_id,
                    topic=topic,
                    db=db,
                )
            except Exception:
                entry["prerequisite_gaps"] = []
            by_topic.append(entry)

        frequent = [
            {
                "id": str(p.id),
                "topic": p.topic,
                "description": p.pattern_description,
                "severity": p.severity,
                "confidence": p.confidence,
                "frequency": p.frequency,
            }
            for p in sorted(patterns, key=lambda x: x.frequency, reverse=True)[:5]
        ]

        trend = await self._calculate_trend(user_id, db)

        return MisconceptionProfile(
            total_patterns=len(patterns),
            unresolved_count=unresolved_count,
            by_topic=by_topic,
            frequent_patterns=frequent,
            improvement_trend=trend,
        )

    async def resolve_pattern(
        self,
        pattern_id: UUID,
        db: AsyncSession,
    ) -> bool:
        result = await db.execute(
            select(MisconceptionPattern).where(MisconceptionPattern.id == pattern_id)
        )
        pattern = result.scalar_one_or_none()
        if not pattern:
            return False
        pattern.resolved = True
        await db.flush()
        await event_logger.log(
            user_id=pattern.user_id,
            event_type="misconception_resolved",
            topic=pattern.topic,
            metadata={
                "pattern_id": str(pattern_id),
                "severity": pattern.severity,
                "method": "single",
            },
            db=db,
        )
        return True

    async def resolve_by_topic(
        self,
        user_id: UUID,
        topic: str,
        db: AsyncSession,
    ) -> int:
        result = await db.execute(
            select(MisconceptionPattern).where(
                MisconceptionPattern.user_id == user_id,
                MisconceptionPattern.topic == topic,
                ~MisconceptionPattern.resolved,
            )
        )
        patterns = list(result.scalars().all())
        count = 0
        for p in patterns:
            p.resolved = True
            count += 1
        await db.flush()
        if count:
            await event_logger.log(
                user_id=user_id,
                event_type="misconception_resolved",
                topic=topic,
                metadata={
                    "pattern_count": count,
                    "method": "batch_topic",
                },
                db=db,
            )
        return count

    async def _calculate_trend(self, user_id: UUID, db: AsyncSession) -> str:
        now = datetime.now(timezone.utc)
        recent = await db.execute(
            select(func.count(MisconceptionPattern.id)).where(
                MisconceptionPattern.user_id == user_id,
                MisconceptionPattern.last_detected_at >= now - timedelta(days=14),
            )
        )
        older = await db.execute(
            select(func.count(MisconceptionPattern.id)).where(
                MisconceptionPattern.user_id == user_id,
                MisconceptionPattern.last_detected_at < now - timedelta(days=14),
                MisconceptionPattern.resolved.is_(False),
            )
        )
        recent_count = recent.scalar() or 0
        older_count = older.scalar() or 0

        if recent_count < older_count and older_count > 0:
            return "improving"
        elif recent_count > older_count:
            return "worsening"
        return "stable"

    async def get_classroom_heatmap(
        self,
        classroom_id: UUID,
        db: AsyncSession,
    ) -> dict:
        enrollments = await db.execute(
            select(ClassEnrollment.student_id).where(ClassEnrollment.class_id == classroom_id)
        )
        student_ids = [row[0] for row in enrollments.all()]
        total_students = len(student_ids)

        if not student_ids:
            return {
                "classroom_id": str(classroom_id),
                "total_students": 0,
                "students_with_misconceptions": 0,
                "total_unresolved_patterns": 0,
                "by_topic": [],
                "improvement_trend": "stable",
                "generated_at": str(datetime.now(timezone.utc)),
            }

        patterns_result = await db.execute(
            select(MisconceptionPattern).where(
                MisconceptionPattern.user_id.in_(student_ids),
                MisconceptionPattern.resolved.is_(False),
            )
        )
        patterns = list(patterns_result.scalars().all())

        students_with_misconceptions = len({p.user_id for p in patterns})

        topic_data: dict[str, dict] = {}
        for p in patterns:
            if p.topic not in topic_data:
                topic_data[p.topic] = {
                    "student_ids": set(),
                    "severity_counts": {},
                    "total_severity_rank": 0,
                    "severity_count": 0,
                    "top_pattern": "",
                    "top_freq": 0,
                }
            td = topic_data[p.topic]
            td["student_ids"].add(p.user_id)
            td["severity_counts"][p.severity] = td["severity_counts"].get(p.severity, 0) + 1
            sev_info = MISCONCEPTION_SEVERITIES.get(
                p.severity, MISCONCEPTION_SEVERITIES["misunderstanding"]
            )
            td["total_severity_rank"] += sev_info["rank"]
            td["severity_count"] += 1
            if p.frequency > td["top_freq"]:
                td["top_freq"] = p.frequency
                td["top_pattern"] = p.pattern_description

        by_topic = []
        for topic, td in sorted(topic_data.items()):
            affected = len(td["student_ids"])
            by_topic.append(
                {
                    "topic": topic,
                    "affected_students": affected,
                    "total_students": total_students,
                    "impact_percentage": round(affected / total_students * 100, 1),
                    "avg_severity_rank": round(td["total_severity_rank"] / td["severity_count"], 1)
                    if td["severity_count"]
                    else 0.0,
                    "severity_distribution": {
                        level: td["severity_counts"].get(level, 0)
                        for level in MISCONCEPTION_SEVERITIES
                    },
                    "top_pattern": td["top_pattern"],
                    "top_pattern_frequency": td["top_freq"],
                }
            )

        return {
            "classroom_id": str(classroom_id),
            "total_students": total_students,
            "students_with_misconceptions": students_with_misconceptions,
            "total_unresolved_patterns": len(patterns),
            "by_topic": by_topic,
            "improvement_trend": "stable",
            "generated_at": str(datetime.now(timezone.utc)),
        }
