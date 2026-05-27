#!/usr/bin/env python3
"""Send daily/weekly digest emails to users who opted in.
Run via cron: 0 8 * * * cd /app && python scripts/send_digests.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

import structlog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select

from src.agents.weak_topic_detection import get_weak_topics
from src.database.models import NotificationPreference, SpacedRepetitionSchedule
from src.database.session import async_session_factory
from src.notifications.email_service import send_email

logger = structlog.get_logger()


async def main():
    factory = async_session_factory()
    template_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "src", "notifications", "templates",
    )
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("digest.html")

    async with factory() as session:
        result = await session.execute(
            select(NotificationPreference).where(
                NotificationPreference.digest_frequency.in_(["daily", "weekly"]),
                NotificationPreference.email_verified,
            )
        )
        prefs_list = list(result.scalars().all())

        now = datetime.now(timezone.utc)

        for prefs in prefs_list:
            try:
                weak_topics = await get_weak_topics(prefs.user_id, session)
                mastery_changes = []
                for wt in weak_topics:
                    mastery_changes.append({
                        "topic": wt["topic"],
                        "improvement": round(wt["average_score"]),
                    })

                due_result = await session.execute(
                    select(SpacedRepetitionSchedule).where(
                        SpacedRepetitionSchedule.user_id == prefs.user_id,
                        SpacedRepetitionSchedule.next_review_at <= now,
                    )
                )
                due = list(due_result.scalars().all())
                due_reviews = [
                    {
                        "topic": d.topic,
                        "days_overdue": (now - d.next_review_at).days,
                    }
                    for d in due
                ]

                html = template.render(
                    frequency=prefs.digest_frequency.capitalize(),
                    mastery_changes=mastery_changes,
                    due_reviews=due_reviews,
                )

                subject = f"{prefs.digest_frequency.capitalize()} Biology Progress Digest"
                await send_email(prefs.email, subject, html)

            except Exception as e:
                logger.error("digest_failed", user_id=prefs.user_id, error=str(e))


if __name__ == "__main__":
    asyncio.run(main())
