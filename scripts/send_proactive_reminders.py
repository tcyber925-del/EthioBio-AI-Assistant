#!/usr/bin/env python3
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select

from src.config import settings
from src.database.models import (
    ParentChild,
    QuizAttempt,
    RecoveryPlan,
    SpacedRepetitionSchedule,
    StudentProfile,
    User,
    UserRole,
)
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

        # ── Parent notifications ──
        parent_result = await session.execute(
            select(User).where(
                User.role == UserRole.parent,
                User.telegram_id.isnot(None),
                User.is_active,
            )
        )
        parents = list(parent_result.scalars().all())

        for parent in parents:
            try:
                children_result = await session.execute(
                    select(User)
                    .join(ParentChild, User.id == ParentChild.student_id)
                    .where(ParentChild.parent_id == parent.id)
                )
                children = list(children_result.scalars().all())
                if not children:
                    continue

                lines = ["👋 *Daily Update*\n"]
                has_activity = False
                for child in children:
                    profile_result = await session.execute(
                        select(StudentProfile).where(StudentProfile.user_id == child.id)
                    )
                    profile = profile_result.scalar_one_or_none()

                    quiz_result = await session.execute(
                        select(QuizAttempt)
                        .where(
                            QuizAttempt.user_id == child.id,
                            QuizAttempt.created_at >= now - timedelta(hours=24),
                        )
                        .order_by(QuizAttempt.created_at.desc())
                        .limit(3)
                    )
                    recent = list(quiz_result.scalars().all())

                    name = child.email or f"Student {str(child.id)[:8]}"
                    grade = child.grade_level or (profile.grade_level if profile else None)
                    lines.append(f"👤 *{name}*{f' (Grade {grade})' if grade else ''}")

                    if recent:
                        has_activity = True
                        for q in recent:
                            pct = q.correct / max(q.total, 1) * 100
                            lines.append(f"  • Quiz: {pct:.0f}% correct")
                    else:
                        lines.append("  No new activity in the last 24h")

                    lines.append("")

                if not has_activity:
                    continue

                url = settings.dashboard_url
                lines.append(
                    f"📋 <a href='{url}/parent'>View full dashboard</a>"
                )

                await bot.send_message(
                    chat_id=parent.telegram_id,
                    text="\n".join(lines),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
                logger.info("parent_reminder_sent", parent_id=str(parent.id))
            except Exception as e:
                logger.warning("parent_reminder_error", parent_id=str(parent.id), error=str(e))

    logger.info("proactive_reminders_done")


if __name__ == "__main__":
    asyncio.run(main())
