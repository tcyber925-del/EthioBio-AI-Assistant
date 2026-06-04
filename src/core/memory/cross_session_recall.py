import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ConversationTurn

logger = structlog.get_logger()

MAX_RECALL_TURNS = 10


class CrossSessionRecall:
    async def record_turns(
        self,
        user_id,
        session_id,
        turns: list[dict],
        topic: str | None,
        db: AsyncSession,
    ) -> None:
        if not turns or not user_id:
            return
        try:
            for turn in turns:
                record = ConversationTurn(
                    user_id=user_id,
                    session_id=session_id,
                    role=turn.get("role", "user"),
                    content=turn.get("content", ""),
                    topic=topic,
                )
                db.add(record)
            await db.flush()
        except Exception as e:
            logger.warning("record_turns_error", error=str(e))

    async def recall_by_topic(
        self,
        user_id,
        topic: str | None,
        db: AsyncSession,
        limit: int = MAX_RECALL_TURNS,
    ) -> list[dict]:
        if not user_id or not topic:
            return []
        try:
            query = (
                select(ConversationTurn)
                .where(
                    ConversationTurn.user_id == user_id,
                    ConversationTurn.topic == topic,
                )
                .order_by(desc(ConversationTurn.created_at))
                .limit(limit)
            )
            result = await db.execute(query)
            records = result.scalars().all()
            return [
                {"role": r.role, "content": r.content, "topic": r.topic}
                for r in records
            ]
        except Exception as e:
            logger.warning("recall_by_topic_error", error=str(e))
            return []

    async def recall_recent(
        self,
        user_id,
        db: AsyncSession,
        limit: int = MAX_RECALL_TURNS,
    ) -> list[dict]:
        if not user_id:
            return []
        try:
            query = (
                select(ConversationTurn)
                .where(ConversationTurn.user_id == user_id)
                .order_by(desc(ConversationTurn.created_at))
                .limit(limit)
            )
            result = await db.execute(query)
            records = result.scalars().all()
            return [
                {"role": r.role, "content": r.content, "topic": r.topic}
                for r in records
            ]
        except Exception as e:
            logger.warning("recall_recent_error", error=str(e))
            return []
