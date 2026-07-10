from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import SemanticFact

logger = structlog.get_logger()


class SemanticFactManager:
    async def upsert(
        self,
        db: AsyncSession,
        user_id: UUID,
        fact_key: str,
        fact_value: str,
        category: str | None = None,
        confidence: float = 0.7,
        source_event_id: UUID | None = None,
    ) -> SemanticFact:
        result = await db.execute(
            select(SemanticFact).where(
                SemanticFact.user_id == user_id,
                SemanticFact.fact_key == fact_key,
                SemanticFact.is_active,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.fact_value = fact_value
            existing.confidence = confidence
            if category:
                existing.category = category
            if source_event_id:
                existing.source_event_id = source_event_id
        else:
            fact = SemanticFact(
                user_id=user_id,
                fact_key=fact_key,
                fact_value=fact_value,
                category=category,
                confidence=confidence,
                source_event_id=source_event_id,
            )
            db.add(fact)
            existing = fact

        await db.flush()
        return existing

    async def get(
        self,
        user_id: UUID,
        fact_key: str,
        db: AsyncSession,
    ) -> SemanticFact | None:
        result = await db.execute(
            select(SemanticFact).where(
                SemanticFact.user_id == user_id,
                SemanticFact.fact_key == fact_key,
                SemanticFact.is_active,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        db: AsyncSession,
        user_id: UUID,
        category: str | None = None,
        limit: int = 50,
    ) -> list[SemanticFact]:
        stmt = select(SemanticFact).where(
            SemanticFact.user_id == user_id,
            SemanticFact.is_active,
        )
        if category:
            stmt = stmt.where(SemanticFact.category == category)
        stmt = stmt.order_by(SemanticFact.updated_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def deactivate(
        self,
        user_id: UUID,
        fact_key: str,
        db: AsyncSession,
    ) -> bool:
        result = await db.execute(
            select(SemanticFact).where(
                SemanticFact.user_id == user_id,
                SemanticFact.fact_key == fact_key,
                SemanticFact.is_active,
            )
        )
        fact = result.scalar_one_or_none()
        if not fact:
            return False
        fact.is_active = False
        await db.flush()
        return True

    async def get_count(self, db: AsyncSession) -> int:
        from sqlalchemy import func

        result = await db.execute(select(func.count(SemanticFact.id)).where(SemanticFact.is_active))
        return result.scalar() or 0
