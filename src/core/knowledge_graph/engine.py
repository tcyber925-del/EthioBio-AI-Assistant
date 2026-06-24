from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

RECURSIVE_CTE = """
WITH RECURSIVE prereq_chain AS (
    SELECT
        tp.topic_id,
        tp.prerequisite_topic_id,
        tp.relationship_type,
        tp.grade_level,
        1 AS depth,
        ARRAY[tp.topic_id, tp.prerequisite_topic_id] AS path
    FROM topic_prerequisites tp
    WHERE tp.topic_id = :start_topic_id

    UNION ALL

    SELECT
        tp.topic_id,
        tp.prerequisite_topic_id,
        tp.relationship_type,
        tp.grade_level,
        pc.depth + 1,
        pc.path || tp.prerequisite_topic_id
    FROM topic_prerequisites tp
    INNER JOIN prereq_chain pc ON pc.prerequisite_topic_id = tp.topic_id
    WHERE NOT tp.prerequisite_topic_id = ANY(pc.path)
)
SELECT DISTINCT
    pc.prerequisite_topic_id AS node_id,
    ct.topic,
    ct.unit,
    ct.grade_level,
    pc.relationship_type,
    pc.depth,
    pc.path
FROM prereq_chain pc
LEFT JOIN curriculum_topics ct ON ct.id = pc.prerequisite_topic_id
ORDER BY pc.depth ASC
"""

DEPENDENT_CTE = """
WITH RECURSIVE dependent_chain AS (
    SELECT
        tp.topic_id,
        tp.prerequisite_topic_id,
        tp.relationship_type,
        tp.grade_level,
        1 AS depth,
        ARRAY[tp.prerequisite_topic_id, tp.topic_id] AS path
    FROM topic_prerequisites tp
    WHERE tp.prerequisite_topic_id = :start_topic_id

    UNION ALL

    SELECT
        tp.topic_id,
        tp.prerequisite_topic_id,
        tp.relationship_type,
        tp.grade_level,
        dc.depth + 1,
        dc.path || tp.topic_id
    FROM topic_prerequisites tp
    INNER JOIN dependent_chain dc ON dc.topic_id = tp.prerequisite_topic_id
    WHERE NOT tp.topic_id = ANY(dc.path)
)
SELECT DISTINCT
    dc.topic_id AS node_id,
    ct.topic,
    ct.unit,
    ct.grade_level,
    dc.relationship_type,
    dc.depth,
    dc.path
FROM dependent_chain dc
LEFT JOIN curriculum_topics ct ON ct.id = dc.topic_id
ORDER BY dc.depth ASC
"""


class GraphReasoningEngine:
    async def get_prerequisite_chain(
        self,
        db: AsyncSession,
        topic_id: UUID,
        max_depth: int = 5,
    ) -> list[dict]:
        result = await db.execute(
            text(RECURSIVE_CTE),
            {"start_topic_id": topic_id},
        )
        rows = result.fetchall()
        return [
            {
                "node_id": str(r.node_id),
                "topic": r.topic,
                "unit": r.unit,
                "grade_level": r.grade_level,
                "relationship_type": r.relationship_type,
                "depth": r.depth,
            }
            for r in rows
            if r.depth <= max_depth
        ]

    async def get_dependent_chain(
        self,
        db: AsyncSession,
        topic_id: UUID,
        max_depth: int = 5,
    ) -> list[dict]:
        result = await db.execute(
            text(DEPENDENT_CTE),
            {"start_topic_id": topic_id},
        )
        rows = result.fetchall()
        return [
            {
                "node_id": str(r.node_id),
                "topic": r.topic,
                "unit": r.unit,
                "grade_level": r.grade_level,
                "relationship_type": r.relationship_type,
                "depth": r.depth,
            }
            for r in rows
            if r.depth <= max_depth
        ]

    async def get_prerequisite_gap_analysis(
        self,
        db: AsyncSession,
        topic_id: UUID,
        user_id: UUID,
    ) -> list[dict]:
        """Find prerequisites the student hasn't mastered yet."""
        from sqlalchemy import select as sa_select

        chain = await self.get_prerequisite_chain(db, topic_id)
        gaps = []
        for node in chain:
            mastery_result = await db.execute(
                sa_select(text("average_score")).from_statement(
                    text(
                        "SELECT average_score FROM student_mastery "
                        "WHERE user_id = :uid AND topic = :topic"
                    )
                ),
                {"uid": user_id, "topic": node["topic"]},
            )
            score_row = mastery_result.fetchone()
            score = score_row[0] if score_row else None
            if score is None or score < 0.6:
                gaps.append({**node, "user_score": score})
        return gaps
