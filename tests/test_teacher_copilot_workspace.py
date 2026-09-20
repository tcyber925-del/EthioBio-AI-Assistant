from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.teacher_copilot.evidence_engine import EvidenceEngine
from src.core.teacher_copilot.pipeline import AssessmentCreatorNode
from src.core.teacher_copilot.state import TeacherCopilotState
from src.database.models import KnowledgeObject, User, UserRole
from src.database.models import Workspace as WorkspaceModel
from src.database.models import WorkspaceMember as WorkspaceMemberModel
from src.database.session import Base

WS_ID = UUID("00000000-0000-0000-0000-00000000000f")
TEACHER_ID = UUID("00000000-0000-0000-0000-00000000000a")
STRANGER_ID = UUID("00000000-0000-0000-0000-00000000000b")
KO_ID = UUID("00000000-0000-0000-0000-00000000000c")


@pytest.fixture
async def session_factory():
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
        db.add(
            KnowledgeObject(
                id=KO_ID,
                workspace_id=WS_ID,
                owner_id=TEACHER_ID,
                title="Cell Structure Notes",
                content_type="application/pdf",
                ko_metadata={"chunk_count": 42},
            )
        )
        await db.commit()

    yield factory
    await engine.dispose()


class TestWorkspaceEvidence:
    async def test_gathers_workspace_knowledge_evidence(self, session_factory):
        async with session_factory() as session:
            engine = EvidenceEngine()
            evidence = await engine.gather_evidence(
                intent="classroom_analysis", user_id=None, session=session, workspace_id=WS_ID
            )

        sources = {e["source"] for e in evidence}
        assert "workspace_knowledge" in sources
        ko = next(e for e in evidence if e["source"] == "workspace_knowledge")
        assert ko["content"]["title"] == "Cell Structure Notes"
        assert ko["content"]["chunk_count"] == 42

    async def test_no_workspace_evidence_when_not_requested(self, session_factory):
        async with session_factory() as session:
            engine = EvidenceEngine()
            evidence = await engine.gather_evidence(
                intent="classroom_analysis", user_id=None, session=session
            )
        assert evidence == []

    def test_format_citations_handles_workspace_knowledge(self):
        citations = EvidenceEngine.format_citations(
            [
                {
                    "source": "workspace_knowledge",
                    "confidence": 0.7,
                    "content": {"title": "Cells", "content_type": "pdf", "chunk_count": 5},
                }
            ]
        )
        assert "Cells" in citations
        assert "5 chunks" in citations


class TestAssessmentGrounding:
    async def test_workspace_context_override_passed_to_quiz_agent(self):
        from src.core.retrieval.models import RetrievalResult, TextMatch

        result = RetrievalResult(
            ko_id="ko-1",
            title="Cell Structure Notes",
            content_type="application/pdf",
            score=0.9,
            matches=[TextMatch(text="mitochondria are the powerhouse", chunk_index=0, score=0.9)],
            workspace_id=str(WS_ID),
        )

        class FakeRouter:
            async def route_and_search(self, query, workspace_id=None, limit=10):
                return [result]

        generate = AsyncMock(
            return_value={"title": "Quiz", "questions": [], "answer_key": ""}
        )

        with patch("src.core.teacher_copilot.pipeline.QuizAgent") as quiz_cls:
            agent_instance = MagicMock()
            agent_instance.generate = generate
            quiz_cls.return_value = agent_instance
            with patch(
                "src.core.retrieval.router.create_knowledge_router",
                return_value=FakeRouter(),
            ):
                node = AssessmentCreatorNode(router=MagicMock())
                state = TeacherCopilotState(
                    user_message="create an assessment about mitochondria",
                    workspace_id=WS_ID,
                )
                await node(state)

        call = generate.await_args
        assert call is not None
        kwargs = call.kwargs
        assert "context_override" in kwargs
        assert "Cell Structure Notes" in kwargs["context_override"]
        assert "mitochondria are the powerhouse" in kwargs["context_override"]

    async def test_no_context_override_without_workspace(self):
        generate = AsyncMock(return_value={"title": "Quiz", "questions": [], "answer_key": ""})

        with patch("src.core.teacher_copilot.pipeline.QuizAgent") as quiz_cls:
            agent_instance = MagicMock()
            agent_instance.generate = generate
            quiz_cls.return_value = agent_instance
            node = AssessmentCreatorNode(router=MagicMock())
            state = TeacherCopilotState(user_message="create an assessment")
            await node(state)

        call = generate.await_args
        assert call is not None
        assert call.kwargs.get("context_override") is None


class TestCopilotWorkspaceAPI:
    def _build(self, session_factory, user_override):
        from fastapi import FastAPI

        import src.api.teacher_copilot as copilot_module
        from src.api.auth import get_current_user
        from src.database.session import get_session

        async def _mock_get_session():
            async with session_factory() as session:
                yield session

        app = FastAPI()
        app.include_router(copilot_module.router)
        app.dependency_overrides[get_session] = _mock_get_session
        app.dependency_overrides[get_current_user] = user_override
        return app, copilot_module

    async def test_member_can_query_with_workspace(self, session_factory):
        from src.core.teacher_copilot.state import TeacherCopilotState

        app, copilot_module = self._build(
            session_factory,
            lambda: User(id=TEACHER_ID, role=UserRole.teacher, is_active=True),
        )

        captured = {}

        async def fake_pipeline_run(initial_state):
            captured["state"] = initial_state
            return TeacherCopilotState(
                user_message=initial_state.user_message,
                response_text="ok",
                intent="classroom_analysis",
                intent_confidence=0.9,
                reasoning="analysis",
                confidence=0.8,
                status="complete",
            )

        with patch.object(
            copilot_module, "build_teacher_pipeline"
        ) as build_pipeline, patch.object(
            copilot_module, "ModelRouter", return_value=MagicMock()
        ):
            build_pipeline.return_value = MagicMock(ainvoke=fake_pipeline_run)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/copilot/query",
                    json={"message": "analyze the class", "workspace_id": str(WS_ID)},
                )
                assert resp.status_code == 200

        assert captured["state"].workspace_id == WS_ID

    async def test_non_member_forbidden(self, session_factory):
        app, copilot_module = self._build(
            session_factory,
            lambda: User(id=STRANGER_ID, role=UserRole.teacher, is_active=True),
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/copilot/query",
                json={"message": "analyze the class", "workspace_id": str(WS_ID)},
            )
            assert resp.status_code == 403

    async def test_query_without_workspace_still_works(self, session_factory):
        from src.core.teacher_copilot.state import TeacherCopilotState

        app, copilot_module = self._build(
            session_factory,
            lambda: User(id=TEACHER_ID, role=UserRole.teacher, is_active=True),
        )

        captured = {}

        async def fake_pipeline_run(initial_state):
            captured["state"] = initial_state
            return TeacherCopilotState(
                user_message=initial_state.user_message,
                response_text="ok",
                intent="classroom_analysis",
                intent_confidence=0.9,
                reasoning="analysis",
                confidence=0.8,
                status="complete",
            )

        with patch.object(
            copilot_module, "build_teacher_pipeline"
        ) as build_pipeline, patch.object(
            copilot_module, "ModelRouter", return_value=MagicMock()
        ):
            build_pipeline.return_value = MagicMock(ainvoke=fake_pipeline_run)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/copilot/query", json={"message": "analyze the class"}
                )
                assert resp.status_code == 200

        assert captured["state"].workspace_id is None
