from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.models import User, UserRole
from src.database.models import Workspace as WorkspaceModel
from src.database.models import WorkspaceMember as WorkspaceMemberModel
from src.database.session import Base

WS_ID = UUID("00000000-0000-0000-0000-00000000000f")
TEACHER_ID = UUID("00000000-0000-0000-0000-00000000000a")
STRANGER_ID = UUID("00000000-0000-0000-0000-00000000000b")


def _agent_result() -> dict:
    return {
        "objective": "Understand mitochondria",
        "explanation": "Mitochondria generate ATP",
        "prior_knowledge": "Cells",
        "activities": [],
        "assessment": "Quiz",
        "model_used": "test",
        "periods": [],
        "exit_ticket": [],
        "differentiation": [],
        "diagram_suggestions": [],
        "misconception_activities": [],
    }


@pytest.fixture
async def lesson_app():
    from fastapi import FastAPI

    import src.api.lesson as lesson_module
    from src.api.auth import get_current_user
    from src.database.session import get_session

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    teacher = User(id=TEACHER_ID, role=UserRole.teacher, is_active=True)
    stranger = User(id=STRANGER_ID, role=UserRole.teacher, is_active=True)
    async with factory() as db:
        db.add_all([teacher, stranger])
        db.add(WorkspaceModel(id=WS_ID, name="Class WS", created_by=TEACHER_ID))
        db.add(WorkspaceMemberModel(workspace_id=WS_ID, user_id=TEACHER_ID, role="owner"))
        await db.commit()

    async def _mock_get_session():
        async with factory() as session:
            yield session

    def _build(user):
        app = FastAPI()
        app.include_router(lesson_module.router)
        app.dependency_overrides[get_session] = _mock_get_session
        app.dependency_overrides[get_current_user] = lambda: user
        return app

    yield factory, lesson_module, _build

    await engine.dispose()


class TestLessonPlanWorkspace:
    async def test_member_generates_plan_grounded_in_workspace(self, lesson_app):
        from src.core.retrieval.models import RetrievalResult, TextMatch

        _, lesson_module, build = lesson_app
        app = build(User(id=TEACHER_ID, role=UserRole.teacher, is_active=True))

        kml_result = RetrievalResult(
            ko_id="ko-1",
            title="Cell Structure Notes",
            content_type="application/pdf",
            score=0.9,
            matches=[TextMatch(text="mitochondria are the powerhouse", chunk_index=0, score=0.9)],
            workspace_id=str(WS_ID),
        )

        class FakeRouter:
            async def route_and_search(self, query, workspace_id=None, limit=10):
                return [kml_result]

        generate = AsyncMock(return_value=_agent_result())

        with patch.object(lesson_module, "LessonPlannerAgent") as agent_cls, patch(
            "src.core.retrieval.router.create_knowledge_router", return_value=FakeRouter()
        ), patch.object(lesson_module, "ModelRouter", return_value=MagicMock()):
            agent_instance = MagicMock()
            agent_instance.generate = generate
            agent_cls.return_value = agent_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/lesson-plan/generate",
                    json={
                        "grade_level": 10,
                        "topic": "mitochondria",
                        "workspace_id": str(WS_ID),
                    },
                )
                assert resp.status_code == 200

        call = generate.await_args
        assert call is not None
        kwargs = call.kwargs
        assert kwargs.get("workspace_context")
        assert "Cell Structure Notes" in kwargs["workspace_context"]
        assert "mitochondria are the powerhouse" in kwargs["workspace_context"]

    async def test_non_member_forbidden(self, lesson_app):
        _, lesson_module, build = lesson_app
        app = build(User(id=STRANGER_ID, role=UserRole.teacher, is_active=True))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/lesson-plan/generate",
                json={
                    "grade_level": 10,
                    "topic": "mitochondria",
                    "workspace_id": str(WS_ID),
                },
            )
            assert resp.status_code == 403

    async def test_no_workspace_skips_grounding(self, lesson_app):
        _, lesson_module, build = lesson_app
        app = build(User(id=TEACHER_ID, role=UserRole.teacher, is_active=True))

        generate = AsyncMock(return_value=_agent_result())

        with patch.object(lesson_module, "LessonPlannerAgent") as agent_cls, patch.object(
            lesson_module, "ModelRouter", return_value=MagicMock()
        ):
            agent_instance = MagicMock()
            agent_instance.generate = generate
            agent_cls.return_value = agent_instance

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/lesson-plan/generate",
                    json={"grade_level": 10, "topic": "mitochondria"},
                )
                assert resp.status_code == 200

        call = generate.await_args
        assert call is not None
        assert call.kwargs.get("workspace_context") is None


class TestLessonPlannerAgentWorkspace:
    async def test_workspace_context_injected_into_prompt(self):
        from src.agents.lesson_planner import LessonPlannerAgent

        agent = LessonPlannerAgent(llm_router=MagicMock())
        agent._call_llm = AsyncMock(
            return_value={"content": '{"objective": "o", "explanation": "e"}', "model": "m"}
        )

        await agent.generate(
            grade_level=10,
            topic="mitochondria",
            workspace_context="[Cell Structure Notes]\nmitochondria are the powerhouse",
        )

        call = agent._call_llm.await_args
        assert call is not None
        user_message = call.kwargs["user_message"]
        assert "Cell Structure Notes" in user_message
        assert "mitochondria are the powerhouse" in user_message
        assert "Workspace Materials" in user_message
