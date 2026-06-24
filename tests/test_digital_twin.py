import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.digital_twin.builder import TwinBuilder
from src.database.models import StudentAbility, StudentDigitalTwin


class TestStudentDigitalTwinModel:
    async def test_create_twin(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        twin = StudentDigitalTwin(
            user_id=user_id,
            knowledge_state={"overall": 0.75, "topics": {}},
            mastery_state={"overall": 0.8, "topics": {}},
            overall_health="healthy",
            confidence=0.9,
        )
        db_session.add(twin)
        await db_session.commit()
        await db_session.refresh(twin)

        assert twin.user_id == user_id
        assert twin.knowledge_state["overall"] == 0.75
        assert twin.overall_health == "healthy"
        assert twin.confidence == 0.9
        assert isinstance(twin.created_at, datetime)

    async def test_twin_defaults(self, db_session: AsyncSession):
        user_id = uuid.uuid4()
        twin = StudentDigitalTwin(user_id=user_id)
        db_session.add(twin)
        await db_session.commit()
        await db_session.refresh(twin)

        assert twin.overall_health == "unknown"
        assert twin.confidence == 0.0
        assert twin.knowledge_state == {}


class TestTwinBuilder:
    async def test_gather_knowledge_state(self, db_session):
        user_id = uuid.uuid4()
        db_session.add(StudentAbility(
            user_id=user_id, topic="Cell Division",
            ability_score=0.72, uncertainty=0.3, attempt_count=8,
        ))
        db_session.add(StudentAbility(
            user_id=user_id, topic="Genetics",
            ability_score=0.88, uncertainty=0.2, attempt_count=12,
        ))
        await db_session.commit()

        builder = TwinBuilder(db_session)
        result = await builder.gather_knowledge_state(user_id)

        assert "overall" in result
        assert "topics" in result
        assert result["topics"]["Cell Division"]["score"] == 0.72
        assert result["topics"]["Genetics"]["score"] == 0.88
        assert result["topics"]["Cell Division"]["data_points"] == 8

    async def test_gather_knowledge_state_empty(self, db_session):
        builder = TwinBuilder(db_session)
        result = await builder.gather_knowledge_state(uuid.uuid4())
        assert result == {}


class TestTwinBuilderRebuild:
    async def test_rebuild_creates_twin(self, db_session):
        user_id = uuid.uuid4()
        db_session.add(StudentAbility(
            user_id=user_id, topic="Cell Division",
            ability_score=0.72, uncertainty=0.3, attempt_count=8,
        ))
        await db_session.commit()

        builder = TwinBuilder(db_session)
        state = await builder.rebuild(user_id)

        assert "knowledge_state" in state
        assert state["overall_health"] in ("healthy", "needs_attention", "unknown")
        assert state["confidence"] >= 0.0

        twin = await db_session.get(StudentDigitalTwin, user_id)
        assert twin is not None
        assert twin.knowledge_state["topics"]["Cell Division"]["score"] == 0.72

    async def test_rebuild_updates_existing(self, db_session):
        user_id = uuid.uuid4()
        db_session.add(StudentDigitalTwin(
            user_id=user_id, overall_health="unknown", confidence=0.0,
        ))
        db_session.add(StudentAbility(
            user_id=user_id, topic="Genetics",
            ability_score=0.9, uncertainty=0.1, attempt_count=15,
        ))
        await db_session.commit()

        builder = TwinBuilder(db_session)
        await builder.rebuild(user_id)

        twin = await db_session.get(StudentDigitalTwin, user_id)
        assert twin.knowledge_state["topics"]["Genetics"]["score"] == 0.9
