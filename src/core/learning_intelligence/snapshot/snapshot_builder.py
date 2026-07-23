import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.learning_intelligence.models import EducationalMemorySummary, LearnerSnapshot
from src.core.learning_intelligence.snapshot.loaders import (
    load_ability,
    load_gamification,
    load_mastery,
    load_memory,
    load_misconceptions,
    load_recovery,
    load_reviews,
)


class SnapshotBuilder:
    LOADERS = [
        ("mastery", load_mastery),
        ("ability", load_ability),
        ("misconceptions", load_misconceptions),
        ("recovery", load_recovery),
        ("reviews", load_reviews),
        ("memory", load_memory),
        ("gamification", load_gamification),
    ]

    async def build(self, session: AsyncSession, user_id: str | UUID) -> LearnerSnapshot:
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        results = await asyncio.gather(
            *(loader(session, uid) for _, loader in self.LOADERS),
            return_exceptions=True,
        )

        snapshot_kwargs: dict = {}
        degraded_sources: list[str] = []

        for (source_name, _), result in zip(self.LOADERS, results, strict=False):
            if isinstance(result, BaseException):
                degraded_sources.append(source_name)
            elif result is not None:
                snapshot_kwargs.update(result)

        edu_memory = snapshot_kwargs.pop("educational_memory", None)
        learning_goals = edu_memory.active_learning_goals if edu_memory is not None else []

        snapshot_kwargs.pop("learning_goals", None)

        return LearnerSnapshot(
            user_id=uid,
            generated_at=datetime.now(timezone.utc),
            educational_memory=edu_memory or EducationalMemorySummary(),
            learning_goals=learning_goals,
            degraded=len(degraded_sources) > 0,
            degraded_sources=degraded_sources,
            **snapshot_kwargs,
        )
