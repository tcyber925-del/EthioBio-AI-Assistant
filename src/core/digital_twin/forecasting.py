from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    SpacedRepetitionSchedule,
    StudentAbility,
    TopicMasteryHistory,
)

logger = structlog.get_logger()

WEEK_SECONDS = 604800


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive(dt: datetime | None) -> datetime | None:
    if dt is not None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class ForecastingEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def forecast_all(
        self,
        user_id: UUID,
        weeks_ahead: int = 4,
    ) -> dict:
        mastery = await self._forecast_mastery(user_id, weeks_ahead)
        retention = await self._forecast_retention(user_id, weeks_ahead)
        readiness = await self._forecast_readiness(user_id, weeks_ahead, mastery)
        risk = await self._forecast_risk(user_id, mastery, retention, readiness)

        return {
            "user_id": str(user_id),
            "weeks_ahead": weeks_ahead,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mastery": mastery,
            "retention": retention,
            "readiness": readiness,
            "risk": risk,
        }

    async def _forecast_mastery(
        self,
        user_id: UUID,
        weeks_ahead: int,
    ) -> list[dict]:
        result = await self.session.execute(
            select(TopicMasteryHistory)
            .where(TopicMasteryHistory.user_id == user_id)
            .order_by(TopicMasteryHistory.topic, TopicMasteryHistory.recorded_at)
        )
        rows = result.scalars().all()

        topics: dict[str, list[dict]] = {}
        for row in rows:
            topic = row.topic
            if topic not in topics:
                topics[topic] = []
            topics[topic].append(
                {
                    "score": row.average_score,
                    "recorded_at": _naive(row.recorded_at),
                }
            )

        forecasts = []
        for topic, history in topics.items():
            if len(history) < 2:
                current = history[-1]["score"] if history else 0.0
                forecasts.append(
                    {
                        "topic": topic,
                        "current": current,
                        "projected": current,
                        "trend": "stable",
                        "confidence": "low",
                        "data_points": len(history),
                    }
                )
                continue

            now = _now()
            recent = history[-10:]
            t_min = recent[0]["recorded_at"].timestamp()

            n = len(recent)
            sum_t = 0.0
            sum_s = 0.0
            sum_tt = 0.0
            sum_ts = 0.0
            for hp in recent:
                t = (hp["recorded_at"].timestamp() - t_min) / WEEK_SECONDS
                s = hp["score"]
                sum_t += t
                sum_s += s
                sum_tt += t * t
                sum_ts += t * s

            slope = (
                (n * sum_ts - sum_t * sum_s) / (n * sum_tt - sum_t * sum_t)
                if (n * sum_tt - sum_t * sum_t != 0)
                else 0.0
            )

            current_score = recent[-1]["score"]
            projected = current_score + slope * weeks_ahead
            projected = max(0.0, min(1.0, projected))

            if slope > 0.02:
                trend = "improving"
            elif slope < -0.02:
                trend = "declining"
            else:
                trend = "stable"

            last_data_days = (now - recent[-1]["recorded_at"]).days
            if n >= 10 and last_data_days < 7:
                confidence = "high"
            elif n >= 5 and last_data_days < 30:
                confidence = "medium"
            else:
                confidence = "low"

            forecasts.append(
                {
                    "topic": topic,
                    "current": round(current_score, 2),
                    "projected": round(projected, 2),
                    "trend": trend,
                    "confidence": confidence,
                    "data_points": len(history),
                }
            )

        return sorted(forecasts, key=lambda f: f["topic"])

    async def _forecast_retention(
        self,
        user_id: UUID,
        weeks_ahead: int,
    ) -> list[dict]:
        result = await self.session.execute(
            select(SpacedRepetitionSchedule).where(
                SpacedRepetitionSchedule.user_id == user_id,
            )
        )
        rows = result.scalars().all()

        now = _now()
        forecasts = []
        for row in rows:
            last = _naive(row.last_reviewed_at)
            if not last:
                forecasts.append(
                    {
                        "topic": row.topic,
                        "current": row.mastery_score,
                        "projected": max(0.0, row.mastery_score * 0.85),
                        "retention_rate": "declining",
                        "confidence": "low",
                    }
                )
                continue

            days_since = (now - last).days
            decay = 1.0 - (days_since / (row.interval_days or 7)) * 0.3
            decay = max(0.0, min(1.0, decay))

            projected_decay = (
                1.0 - ((days_since + weeks_ahead * 7) / (row.interval_days or 7)) * 0.3
            )
            projected_decay = max(0.0, min(1.0, projected_decay))

            projected = row.mastery_score * projected_decay
            current = row.mastery_score * decay

            rate = "stable"
            if projected < current - 0.05:
                rate = "declining"
            elif projected > current + 0.05:
                rate = "improving"

            forecasts.append(
                {
                    "topic": row.topic,
                    "current": round(current, 2),
                    "projected": round(projected, 2),
                    "retention_rate": rate,
                    "confidence": "medium" if row.review_count >= 3 else "low",
                }
            )

        return sorted(forecasts, key=lambda f: f["topic"])

    async def _forecast_readiness(
        self,
        user_id: UUID,
        weeks_ahead: int,
        mastery_forecast: list[dict],
    ) -> dict:
        result = await self.session.execute(
            select(StudentAbility).where(
                StudentAbility.user_id == user_id,
            )
        )
        abilities = {r.topic: r.ability_score for r in result.scalars().all()}

        mastery_map = {f["topic"]: f for f in mastery_forecast}

        total_current = 0.0
        total_projected = 0.0
        count = 0
        topic_readiness = []
        for topic, ability in abilities.items():
            mf = mastery_map.get(topic, {})
            current_mastery = mf.get("current", 0.5)
            projected_mastery = mf.get("projected", current_mastery)

            current = ability * 0.6 + current_mastery * 0.4
            projected = ability * 0.6 + projected_mastery * 0.4

            total_current += current
            total_projected += projected
            count += 1

            topic_readiness.append(
                {
                    "topic": topic,
                    "current": round(current, 2),
                    "projected": round(projected, 2),
                }
            )

        overall_current = round(total_current / count, 2) if count else 0.0
        overall_projected = round(total_projected / count, 2) if count else 0.0

        return {
            "overall": {
                "current": overall_current,
                "projected": overall_projected,
            },
            "topic": topic_readiness,
        }

    async def _forecast_risk(
        self,
        user_id: UUID,
        mastery_forecast: list[dict],
        retention_forecast: list[dict],
        readiness_forecast: dict,
    ) -> list[dict]:
        risks = []
        retention_map = {f["topic"]: f for f in retention_forecast}

        readiness_topics = {r["topic"]: r for r in readiness_forecast.get("topic", [])}

        for mf in mastery_forecast:
            topic = mf["topic"]
            projected = mf["projected"]
            if projected < 0.5:
                risks.append(
                    {
                        "topic": topic,
                        "type": "mastery_decline",
                        "severity": "high" if projected < 0.3 else "medium",
                        "current": mf["current"],
                        "projected": projected,
                        "detail": f"Mastery projected to drop to {round(projected * 100)}%",
                    }
                )

            rf = retention_map.get(topic, {})
            retention_projected = rf.get("projected", 1.0)
            if retention_projected < 0.5:
                risks.append(
                    {
                        "topic": topic,
                        "type": "retention_loss",
                        "severity": "high" if retention_projected < 0.3 else "medium",
                        "current": rf.get("current", 1.0),
                        "projected": retention_projected,
                        "detail": f"Retention projected at {round(retention_projected * 100)}%",
                    }
                )

            rd = readiness_topics.get(topic, {})
            readiness_projected = rd.get("projected", 1.0)
            if readiness_projected < 0.5:
                risks.append(
                    {
                        "topic": topic,
                        "type": "readiness_gap",
                        "severity": "high" if readiness_projected < 0.3 else "medium",
                        "current": rd.get("current", 1.0),
                        "projected": readiness_projected,
                        "detail": f"Readiness projected at {round(readiness_projected * 100)}%",
                    }
                )

        return sorted(risks, key=lambda r: (0 if r["severity"] == "high" else 1, r["topic"]))

    async def forecast_mastery_topic(
        self,
        user_id: UUID,
        topic: str,
        weeks_ahead: int = 4,
    ) -> dict:
        all_mastery = await self._forecast_mastery(user_id, weeks_ahead)
        for f in all_mastery:
            if f["topic"] == topic:
                return f
        return {
            "topic": topic,
            "current": 0.0,
            "projected": 0.0,
            "trend": "unknown",
            "confidence": "low",
            "data_points": 0,
        }
