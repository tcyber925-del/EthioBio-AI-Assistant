#!/usr/bin/env python3
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone

import structlog
from sqlalchemy import select

from src.config import settings
from src.database.models import RecoveryPlan, SpacedRepetitionSchedule, User
from src.database.session import async_session_factory

logger = structlog.get_logger()


async def main():
    if not settings.telegram_bot_token:
        logger.warning("telegram_not_configured")
        return

    import telegram

    bot = telegram.Bot(token=settings.telegram_bot_token)

    factory = async_session_factory()
    now = datetime.now(timezone.utc)

    async with factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id.isnot(None), User.is_active)
        )
        users = list(result.scalars().all())
        logger.info("proactive_reminders_start", user_count=len(users))

        for user in users:
            try:
                lines: list[str] = []

                due_reviews = await session.execute(
                    select(SpacedRepetitionSchedule).where(
                        SpacedRepetitionSchedule.user_id == user.id,
                        SpacedRepetitionSchedule.next_review_at <= now,
                    )
                )
                due_count = len(list(due_reviews.scalars().all()))

                if due_count > 0:
                    label = "reviews" if due_count > 1 else "review"
                    lines.append(f"📚 *Due Reviews:* {due_count} {label} due today.")

                active_plans = await session.execute(
                    select(RecoveryPlan).where(
                        RecoveryPlan.user_id == user.id,
                        RecoveryPlan.status == "active",
                    )
                )
                plans = list(active_plans.scalars().all())

                for plan in plans:
                    pct = round(plan.completed_tasks / max(plan.total_tasks, 1) * 100)
                    remaining = plan.total_tasks - plan.completed_tasks
                    lines.append(
                        f"📋 *Recovery:* {plan.topic} — {pct}% complete"
                        f" ({remaining} task{'s' if remaining > 1 else ''} remaining)."
                    )

                if lines:
                    text = "🌱 *Your Learning Summary*\n\n" + "\n".join(lines)
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=text,
                        parse_mode="Markdown",
                    )
                    logger.info("reminder_sent", user_id=user.id, telegram_id=user.telegram_id)
            except Exception as e:
                logger.error("reminder_failed", user_id=user.id, error=str(e))

    logger.info("proactive_reminders_done")


if __name__ == "__main__":
    asyncio.run(main())
