from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import CurriculumTopic, TopicPrerequisite

logger = structlog.get_logger()


class RelationshipBuilder:
    async def add_prerequisite(
        self,
        db: AsyncSession,
        topic_id: UUID,
        prerequisite_topic_id: UUID,
        relationship_type: str = "prerequisite",
    ) -> TopicPrerequisite:
        existing = await db.execute(
            select(TopicPrerequisite).where(
                TopicPrerequisite.topic_id == topic_id,
                TopicPrerequisite.prerequisite_topic_id == prerequisite_topic_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Prerequisite relationship already exists")

        # Look up grade_level from either topic
        topic = await db.get(CurriculumTopic, topic_id)
        grade_level = topic.grade_level if topic else 0

        prereq = TopicPrerequisite(
            topic_id=topic_id,
            prerequisite_topic_id=prerequisite_topic_id,
            relationship_type=relationship_type,
            grade_level=grade_level,
        )
        db.add(prereq)
        await db.flush()
        logger.info(
            "prerequisite_added",
            topic_id=str(topic_id),
            prereq_id=str(prerequisite_topic_id),
        )
        return prereq

    async def add_batch(
        self,
        db: AsyncSession,
        topic_id: UUID,
        prerequisite_ids: list[UUID],
        relationship_type: str = "prerequisite",
    ) -> list[TopicPrerequisite]:
        created = []
        for pid in prerequisite_ids:
            try:
                prereq = await self.add_prerequisite(db, topic_id, pid, relationship_type)
                created.append(prereq)
            except ValueError:
                continue
        return created

    async def get_prerequisites(
        self,
        db: AsyncSession,
        topic_id: UUID,
    ) -> list[TopicPrerequisite]:
        result = await db.execute(
            select(TopicPrerequisite).where(
                TopicPrerequisite.topic_id == topic_id,
            )
        )
        return list(result.scalars().all())

    async def get_dependents(
        self,
        db: AsyncSession,
        topic_id: UUID,
    ) -> list[TopicPrerequisite]:
        result = await db.execute(
            select(TopicPrerequisite).where(
                TopicPrerequisite.prerequisite_topic_id == topic_id,
            )
        )
        return list(result.scalars().all())

    async def remove(
        self,
        db: AsyncSession,
        prereq_id: UUID,
    ) -> bool:
        prereq = await db.get(TopicPrerequisite, prereq_id)
        if not prereq:
            return False
        await db.delete(prereq)
        await db.flush()
        return True
