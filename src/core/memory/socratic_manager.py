from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemorySocraticState

logger = structlog.get_logger()


class SocraticManager:
    async def get_state(
        self,
        user_id: UUID,
        topic: str,
        db: AsyncSession,
    ) -> MemorySocraticState | None:
        result = await db.execute(
            select(MemorySocraticState).where(
                MemorySocraticState.user_id == user_id,
                MemorySocraticState.topic == topic,
            )
        )
        return result.scalar_one_or_none()

    async def update_state(
        self,
        user_id: UUID,
        topic: str,
        updates: dict,
        db: AsyncSession,
    ) -> MemorySocraticState:
        state = await self.get_state(user_id, topic, db)
        if state:
            for key, value in updates.items():
                if hasattr(state, key) and value is not None:
                    setattr(state, key, value)
            state.updated_at = datetime.now(timezone.utc)
        else:
            state = MemorySocraticState(
                user_id=user_id,
                topic=topic,
                socratic_stage=updates.get("socratic_stage", "guided_discovery"),
                current_focus=updates.get("current_focus"),
                student_understanding=updates.get("student_understanding", "none"),
                next_question=updates.get("next_question"),
                conceptual_gaps=updates.get("conceptual_gaps", []),
            )
            db.add(state)

        await db.flush()
        await db.refresh(state)
        return state

    async def clear_state(self, user_id: UUID, topic: str, db: AsyncSession) -> bool:
        state = await self.get_state(user_id, topic, db)
        if state:
            await db.delete(state)
            await db.flush()
            logger.info("socratic_state_cleared", user_id=str(user_id), topic=topic)
            return True
        return False
