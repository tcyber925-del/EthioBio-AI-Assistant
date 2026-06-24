import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.digital_twin.forecasting import ForecastingEngine
from src.core.digital_twin.simulation import SimulationEngine
from src.database.models import (
    SpacedRepetitionSchedule,
    StudentAbility,
    TopicMasteryHistory,
)

NOW = datetime.now(timezone.utc)


class TestForecastMastery:
    async def test_empty_history(self, db_session: AsyncSession):
        engine = ForecastingEngine(db_session)
        result = await engine.forecast_all(uuid.uuid4())

        assert result["mastery"] == []
        assert result["retention"] == []
        assert result["readiness"]["overall"]["current"] == 0.0

    async def test_single_data_point(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        db_session.add(TopicMasteryHistory(
            user_id=user_id, topic="Cell Division", unit="Unit 1",
            grade_level=10, average_score=0.7, attempt_count=5,
            severity="low", confidence=0.8, source="quiz",
            recorded_at=NOW - timedelta(days=1),
        ))
        await db_session.commit()

        engine = ForecastingEngine(db_session)
        result = await engine.forecast_all(user_id)

        assert len(result["mastery"]) == 1
        m = result["mastery"][0]
        assert m["topic"] == "Cell Division"
        assert m["current"] == 0.7
        assert m["projected"] == 0.7
        assert m["confidence"] == "low"

    async def test_improving_trend(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        for i, score in enumerate([0.3, 0.4, 0.5, 0.6, 0.7]):
            db_session.add(TopicMasteryHistory(
                user_id=user_id, topic="Genetics", unit="Unit 2",
                grade_level=10, average_score=score, attempt_count=5,
                severity="low", confidence=0.8, source="quiz",
                recorded_at=NOW - timedelta(days=(5 - i)),
            ))
        await db_session.commit()

        engine = ForecastingEngine(db_session)
        result = await engine.forecast_all(user_id)

        m = result["mastery"][0]
        assert m["trend"] == "improving"
        assert m["projected"] > m["current"]

    async def test_declining_trend(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        for i, score in enumerate([0.8, 0.7, 0.6, 0.5, 0.4]):
            db_session.add(TopicMasteryHistory(
                user_id=user_id, topic="Cell Division", unit="Unit 1",
                grade_level=10, average_score=score, attempt_count=5,
                severity="low", confidence=0.8, source="quiz",
                recorded_at=NOW - timedelta(days=(5 - i)),
            ))
        await db_session.commit()

        engine = ForecastingEngine(db_session)
        result = await engine.forecast_all(user_id)

        m = result["mastery"][0]
        assert m["trend"] == "declining"
        assert m["projected"] < m["current"]

    async def test_confidence_high(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        for i in range(12):
            db_session.add(TopicMasteryHistory(
                user_id=user_id, topic="Genetics", unit="Unit 2",
                grade_level=10, average_score=0.5 + (i * 0.03),
                attempt_count=5, severity="low", confidence=0.8,
                source="quiz",
                recorded_at=NOW - timedelta(days=(11 - i)),
            ))
        await db_session.commit()

        engine = ForecastingEngine(db_session)
        result = await engine.forecast_all(user_id)

        assert result["mastery"][0]["confidence"] == "high"


class TestForecastRetention:
    async def test_with_recent_review(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        db_session.add(SpacedRepetitionSchedule(
            user_id=user_id, topic="Cell Division", unit="Unit 1",
            grade_level=10, mastery_score=0.85, interval_days=7,
            ease_factor=2.5, next_review_at=NOW + timedelta(days=5),
            last_reviewed_at=NOW - timedelta(days=1),
            review_count=5,
        ))
        await db_session.commit()

        engine = ForecastingEngine(db_session)
        result = await engine.forecast_all(user_id)

        assert len(result["retention"]) == 1
        r = result["retention"][0]
        assert r["topic"] == "Cell Division"
        assert r["current"] > 0.7
        assert r["confidence"] == "medium"

    async def test_no_last_reviewed(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        db_session.add(SpacedRepetitionSchedule(
            user_id=user_id, topic="Genetics", unit="Unit 2",
            grade_level=10, mastery_score=0.75, interval_days=7,
            ease_factor=2.5, next_review_at=NOW + timedelta(days=5),
            review_count=0, last_reviewed_at=None,
        ))
        await db_session.commit()

        engine = ForecastingEngine(db_session)
        result = await engine.forecast_all(user_id)

        r = result["retention"][0]
        assert r["confidence"] == "low"


class TestForecastReadiness:
    async def test_with_ability_and_mastery(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        db_session.add(StudentAbility(
            user_id=user_id, topic="Cell Division",
            ability_score=0.8, uncertainty=0.2, attempt_count=10,
        ))
        db_session.add(TopicMasteryHistory(
            user_id=user_id, topic="Cell Division", unit="Unit 1",
            grade_level=10, average_score=0.7, attempt_count=5,
            severity="low", confidence=0.8, source="quiz",
            recorded_at=NOW - timedelta(days=1),
        ))
        await db_session.commit()

        engine = ForecastingEngine(db_session)
        result = await engine.forecast_all(user_id)

        assert result["readiness"]["overall"]["current"] > 0.0
        assert len(result["readiness"]["topic"]) == 1
        assert result["readiness"]["topic"][0]["topic"] == "Cell Division"


class TestForecastRisk:
    async def test_identifies_declining_mastery_risk(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        for i, score in enumerate([0.8, 0.7, 0.6, 0.5, 0.4]):
            db_session.add(TopicMasteryHistory(
                user_id=user_id, topic="Cell Division", unit="Unit 1",
                grade_level=10, average_score=score, attempt_count=5,
                severity="low", confidence=0.8, source="quiz",
                recorded_at=NOW - timedelta(days=(5 - i)),
            ))
        await db_session.commit()

        engine = ForecastingEngine(db_session)
        result = await engine.forecast_all(user_id)

        risks = result["risk"]
        risk_types = {r["type"] for r in risks}
        assert "mastery_decline" in risk_types
        assert any(r["topic"] == "Cell Division" for r in risks)


class TestForecastMasteryTopic:
    async def test_single_topic_forecast(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        for i, score in enumerate([0.3, 0.4, 0.5, 0.6, 0.7]):
            db_session.add(TopicMasteryHistory(
                user_id=user_id, topic="Genetics", unit="Unit 2",
                grade_level=10, average_score=score, attempt_count=5,
                severity="low", confidence=0.8, source="quiz",
                recorded_at=NOW - timedelta(days=(5 - i)),
            ))
        await db_session.commit()

        engine = ForecastingEngine(db_session)
        result = await engine.forecast_mastery_topic(user_id, "Genetics")

        assert result["topic"] == "Genetics"
        assert result["current"] == 0.7
        assert result["trend"] == "improving"

    async def test_unknown_topic(self, db_session: AsyncSession):
        engine = ForecastingEngine(db_session)
        result = await engine.forecast_mastery_topic(
            uuid.uuid4(), "Nonexistent",
        )

        assert result["topic"] == "Nonexistent"
        assert result["current"] == 0.0
        assert result["trend"] == "unknown"


class TestSimulationEngine:
    async def test_empty_actions_returns_baseline_only(self, db_session):
        engine = SimulationEngine(db_session)
        result = await engine.simulate(uuid.uuid4(), [])

        assert result["baseline"] is not None
        assert result["simulated"] is None
        assert result["actions"] == []

    async def test_boost_mastery(self, db_session):
        user_id = uuid.uuid4()
        for i, score in enumerate([0.3, 0.4, 0.5, 0.6, 0.7]):
            db_session.add(TopicMasteryHistory(
                user_id=user_id, topic="Cell Division", unit="Unit 1",
                grade_level=10, average_score=score, attempt_count=5,
                severity="low", confidence=0.8, source="quiz",
                recorded_at=NOW - timedelta(days=(5 - i)),
            ))
        await db_session.commit()

        engine = SimulationEngine(db_session)
        result = await engine.simulate(user_id, [
            {"type": "boost_mastery", "topic": "Cell Division", "value": 0.2},
        ])

        sim = result["simulated"]
        assert sim is not None
        sim_m = {f["topic"]: f for f in sim["mastery"]}
        base_m = {f["topic"]: f for f in result["baseline"]["mastery"]}

        assert sim_m["Cell Division"]["current"] > base_m["Cell Division"]["current"]
        assert sim_m["Cell Division"]["trend"] == "improving"

    async def test_add_reviews(self, db_session):
        user_id = uuid.uuid4()
        db_session.add(SpacedRepetitionSchedule(
            user_id=user_id, topic="Cell Division", unit="Unit 1",
            grade_level=10, mastery_score=0.7, interval_days=7,
            ease_factor=2.5, next_review_at=NOW + timedelta(days=5),
            last_reviewed_at=NOW - timedelta(days=14),
            review_count=2,
        ))
        await db_session.commit()

        engine = SimulationEngine(db_session)
        result = await engine.simulate(user_id, [
            {"type": "add_reviews", "topic": "Cell Division", "value": 3},
        ])

        sim = result["simulated"]
        assert sim is not None
        sim_r = {f["topic"]: f for f in sim["retention"]}
        base_r = {f["topic"]: f for f in result["baseline"]["retention"]}

        assert sim_r["Cell Division"]["current"] > base_r["Cell Division"]["current"]

    async def test_resolve_misconception(self, db_session):
        user_id = uuid.uuid4()
        for i, score in enumerate([0.7, 0.65, 0.6, 0.55, 0.5]):
            db_session.add(TopicMasteryHistory(
                user_id=user_id, topic="Genetics", unit="Unit 2",
                grade_level=10, average_score=score, attempt_count=5,
                severity="low", confidence=0.8, source="quiz",
                recorded_at=NOW - timedelta(days=(5 - i)),
            ))
        await db_session.commit()

        engine = SimulationEngine(db_session)
        result = await engine.simulate(user_id, [
            {"type": "resolve_misconception", "topic": "Genetics"},
        ])

        sim = result["simulated"]
        assert sim is not None
        sim_m = {f["topic"]: f for f in sim["mastery"]}
        base_m = {f["topic"]: f for f in result["baseline"]["mastery"]}

        assert sim_m["Genetics"]["projected"] > base_m["Genetics"]["projected"]

    async def test_multiple_actions(self, db_session):
        user_id = uuid.uuid4()
        for t in ["Cell Division", "Genetics"]:
            for i, score in enumerate([0.2, 0.25, 0.3, 0.35, 0.4]):
                db_session.add(TopicMasteryHistory(
                    user_id=user_id, topic=t, unit="Unit 1",
                    grade_level=10, average_score=score, attempt_count=5,
                    severity="low", confidence=0.8, source="quiz",
                    recorded_at=NOW - timedelta(days=(5 - i)),
                ))
        await db_session.commit()

        engine = SimulationEngine(db_session)
        result = await engine.simulate(user_id, [
            {"type": "boost_mastery", "topic": "Cell Division", "value": 0.1},
            {"type": "boost_mastery", "topic": "Genetics", "value": 0.15},
        ])

        sim = result["simulated"]
        assert sim is not None
        assert result["actions"] == [
            {"type": "boost_mastery", "topic": "Cell Division", "value": 0.1},
            {"type": "boost_mastery", "topic": "Genetics", "value": 0.15},
        ]

        for f in sim["mastery"]:
            base = {m["topic"]: m for m in result["baseline"]["mastery"]}[f["topic"]]
            assert f["current"] > base["current"]
