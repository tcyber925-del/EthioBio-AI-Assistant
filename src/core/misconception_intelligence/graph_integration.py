from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.knowledge_graph import GraphReasoningEngine
from src.database.models import CurriculumTopic, MisconceptionPattern

logger = structlog.get_logger()


class MisconceptionGraphIntegrator:
    """Links misconception data to the curriculum knowledge graph.

    Surfaces prerequisite knowledge gaps that may be root causes
    of observed misconceptions, and identifies topics most affected
    by misconception cascades.
    """

    def __init__(self):
        self._graph = GraphReasoningEngine()

    async def get_prerequisite_gaps(
        self,
        user_id: UUID,
        topic: str,
        db: AsyncSession,
    ) -> list[dict]:
        topic_node = await self._resolve_topic_node(topic, db)
        if not topic_node:
            logger.info("prerequisite_gap_no_topic_node", topic=topic)
            return []

        chain = await self._graph.get_prerequisite_chain(db, topic_node.id)
        gaps = []
        for node in chain:
            row = await db.execute(
                select(MisconceptionPattern)
                .where(
                    MisconceptionPattern.user_id == user_id,
                    MisconceptionPattern.topic == node["topic"],
                    MisconceptionPattern.resolved.is_(False),
                )
                .order_by(MisconceptionPattern.frequency.desc())
            )
            misconceptions = row.scalars().all()

            from sqlalchemy import text

            mastery_row = await db.execute(
                text(
                    "SELECT average_score FROM student_mastery "
                    "WHERE user_id = :uid AND topic = :topic"
                ),
                {"uid": user_id, "topic": node["topic"]},
            )
            score = mastery_row.fetchone()

            gaps.append(
                {
                    "topic": node["topic"],
                    "unit": node.get("unit"),
                    "depth": node["depth"],
                    "mastery_score": float(score[0]) if score else None,
                    "misconception_count": len(misconceptions),
                    "misconceptions": [
                        {
                            "description": p.pattern_description,
                            "severity": p.severity,
                            "frequency": p.frequency,
                        }
                        for p in misconceptions[:3]
                    ],
                }
            )
        return gaps

    async def get_misconception_cascade(
        self,
        user_id: UUID,
        db: AsyncSession,
    ) -> list[dict]:
        unresolved = await db.execute(
            select(MisconceptionPattern)
            .where(
                MisconceptionPattern.user_id == user_id,
                MisconceptionPattern.resolved.is_(False),
            )
            .order_by(MisconceptionPattern.frequency.desc())
        )
        patterns = unresolved.scalars().all()
        seen_topics = set()
        cascade = []
        for p in patterns:
            if p.topic in seen_topics:
                continue
            seen_topics.add(p.topic)
            gaps = await self.get_prerequisite_gaps(user_id, p.topic, db)
            if gaps:
                cascade.append(
                    {
                        "topic": p.topic,
                        "frequency": p.frequency,
                        "severity": p.severity,
                        "prerequisite_gaps": gaps,
                    }
                )
        return cascade

    async def get_topic_misconception_weight(
        self,
        db: AsyncSession,
        grade_level: int | None = None,
    ) -> list[dict]:
        stmt = select(
            CurriculumTopic.topic,
            CurriculumTopic.unit,
            CurriculumTopic.grade_level,
        )
        if grade_level:
            stmt = stmt.where(CurriculumTopic.grade_level == grade_level)
        stmt = stmt.distinct()
        rows = (await db.execute(stmt)).all()

        weights = []
        for r in rows:
            count_result = await db.execute(
                select(MisconceptionPattern).where(
                    MisconceptionPattern.topic == r.topic,
                    MisconceptionPattern.resolved.is_(False),
                )
            )
            count = len(count_result.scalars().all())
            if count > 0:
                weights.append(
                    {
                        "topic": r.topic,
                        "unit": r.unit,
                        "grade_level": r.grade_level,
                        "active_misconception_count": count,
                    }
                )
        return sorted(weights, key=lambda w: w["active_misconception_count"], reverse=True)

    async def _resolve_topic_node(
        self,
        topic: str,
        db: AsyncSession,
    ) -> CurriculumTopic | None:
        result = await db.execute(
            select(CurriculumTopic)
            .where(
                CurriculumTopic.topic == topic,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
