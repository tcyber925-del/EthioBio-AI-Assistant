import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import StudentDigitalTwin


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
