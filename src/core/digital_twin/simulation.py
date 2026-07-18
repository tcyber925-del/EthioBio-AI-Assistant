from __future__ import annotations

import copy
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.digital_twin.forecasting import ForecastingEngine

logger = structlog.get_logger()


class SimulationEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def simulate(
        self,
        user_id: UUID,
        actions: list[dict],
        weeks_ahead: int = 4,
    ) -> dict:
        engine = ForecastingEngine(self.session)
        baseline = await engine.forecast_all(user_id, weeks_ahead)

        if not actions:
            return {
                "user_id": str(user_id),
                "weeks_ahead": weeks_ahead,
                "baseline": {
                    "mastery": baseline["mastery"],
                    "retention": baseline["retention"],
                    "readiness": baseline["readiness"],
                    "risk": baseline["risk"],
                },
                "simulated": None,
                "actions": [],
            }

        sim_mastery = copy.deepcopy(baseline["mastery"])
        sim_retention = copy.deepcopy(baseline["retention"])

        mastery_map = {f["topic"]: f for f in sim_mastery}
        retention_map = {f["topic"]: f for f in sim_retention}

        for action in actions:
            action_type = action.get("type")
            topic = action.get("topic", "")
            value = action.get("value", 0.0)

            if action_type == "boost_mastery" and topic in mastery_map:
                mf = mastery_map[topic]
                delta = min(max(value, 0.0), 1.0 - mf["current"])
                mf["current"] = round(mf["current"] + delta, 2)
                mf["projected"] = round(min(mf["projected"] + delta * 0.7, 1.0), 2)
                if mf["projected"] > mf["current"]:
                    mf["trend"] = "improving"

            elif action_type == "add_reviews" and topic in retention_map:
                rf = retention_map[topic]
                extra = min(int(value), 10)
                boost = extra * 0.04
                rf["current"] = round(min(rf["current"] + boost, 1.0), 2)
                rf["projected"] = round(min(rf["projected"] + boost * 0.6, 1.0), 2)
                if rf["projected"] >= rf["current"] - 0.02:
                    rf["retention_rate"] = "stable"

            elif action_type == "resolve_misconception":
                for mf in sim_mastery:
                    if topic and mf["topic"] != topic:
                        continue
                    mf["projected"] = round(
                        min(mf["projected"] + 0.15, 1.0),
                        2,
                    )
                    if mf["projected"] > mf["current"]:
                        mf["trend"] = "improving"

        # Recompute readiness with simulated mastery
        sim_readiness = await engine._forecast_readiness(
            user_id,
            weeks_ahead,
            sim_mastery,
        )

        # Recompute risk with simulated forecasts
        sim_risk = await engine._forecast_risk(
            user_id,
            sim_mastery,
            sim_retention,
            sim_readiness,
        )

        return {
            "user_id": str(user_id),
            "weeks_ahead": weeks_ahead,
            "baseline": {
                "mastery": baseline["mastery"],
                "retention": baseline["retention"],
                "readiness": baseline["readiness"],
                "risk": baseline["risk"],
            },
            "simulated": {
                "mastery": sim_mastery,
                "retention": sim_retention,
                "readiness": sim_readiness,
                "risk": sim_risk,
            },
            "actions": actions,
        }
