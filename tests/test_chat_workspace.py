from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.models import User, UserRole
from src.database.models import Workspace as WorkspaceModel
from src.database.models import WorkspaceMember as WorkspaceMemberModel
from src.database.session import Base
from src.schemas.conversation import ConversationResponse

WS_ID = UUID("00000000-0000-0000-0000-00000000000f")
TEACHER_ID = UUID("00000000-0000-0000-0000-00000000000a")
STRANGER_ID = UUID("00000000-0000-0000-0000-00000000000b")
ADMIN_ID = UUID("00000000-0000-0000-0000-00000000000c")


@pytest.fixture
async def chat_app():
    from fastapi import FastAPI

    import src.api.chat as chat_module
    from src.api.auth import get_current_user
    from src.database.session import get_session

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    teacher = User(id=TEACHER_ID, role=UserRole.teacher, is_active=True)
    stranger = User(id=STRANGER_ID, role=UserRole.teacher, is_active=True)
    admin = User(id=ADMIN_ID, role=UserRole.admin, is_active=True)
    async with factory() as db:
        db.add_all([teacher, stranger, admin])
        db.add(WorkspaceModel(id=WS_ID, name="Class WS", created_by=TEACHER_ID))
        db.add(
            WorkspaceMemberModel(
                workspace_id=WS_ID, user_id=TEACHER_ID, role="owner"
            )
        )
        await db.commit()

    async def _mock_get_session():
        async with factory() as session:
            yield session

    async def _member():
        return teacher

    async def _stranger():
        return stranger

    async def _admin():
        return admin

    def _build(user_override):
        app = FastAPI()
        app.include_router(chat_module.router)
        app.dependency_overrides[get_session] = _mock_get_session
        app.dependency_overrides[get_current_user] = user_override
        return app

    chat_module.conversation_service.process = AsyncMock(
        return_value=ConversationResponse(answer="test answer", language="en")
    )

    yield factory, chat_module, _build

    await engine.dispose()


async def _chat(client: AsyncClient, headers: dict | None = None) -> int:
    resp = await client.post(
        "/chat",
        json={"question": "explain mitochondria", "grade_level": 10},
        headers=headers or {},
    )
    return resp


class TestChatWorkspace:
    async def test_member_can_chat_with_workspace(self, chat_app):
        _, chat_module, build = chat_app

        async def _member():
            from src.database.models import User

            return User(id=TEACHER_ID, role=UserRole.teacher, is_active=True)

        app = build(_member)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await _chat(client, {"X-Workspace-Id": str(WS_ID)})
            assert resp.status_code == 200
            assert resp.json()["answer"] == "test answer"

        call = chat_module.conversation_service.process.await_args
        assert call is not None
        conv_request = call.args[0]
        assert conv_request.metadata["workspace_id"] == str(WS_ID)

    async def test_non_member_forbidden(self, chat_app):
        _, _, build = chat_app

        async def _stranger():
            from src.database.models import User

            return User(id=STRANGER_ID, role=UserRole.teacher, is_active=True)

        app = build(_stranger)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await _chat(client, {"X-Workspace-Id": str(WS_ID)})
            assert resp.status_code == 403

    async def test_admin_bypasses_membership(self, chat_app):
        _, chat_module, build = chat_app

        async def _admin():
            from src.database.models import User

            return User(id=ADMIN_ID, role=UserRole.admin, is_active=True)

        app = build(_admin)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await _chat(client, {"X-Workspace-Id": str(WS_ID)})
            assert resp.status_code == 200

    async def test_invalid_workspace_id_returns_400(self, chat_app):
        _, _, build = chat_app

        async def _member():
            from src.database.models import User

            return User(id=TEACHER_ID, role=UserRole.teacher, is_active=True)

        app = build(_member)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await _chat(client, {"X-Workspace-Id": "not-a-uuid"})
            assert resp.status_code == 400

    async def test_chat_without_workspace_still_works(self, chat_app):
        _, chat_module, build = chat_app

        async def _member():
            from src.database.models import User

            return User(id=TEACHER_ID, role=UserRole.teacher, is_active=True)

        app = build(_member)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await _chat(client)
            assert resp.status_code == 200

        call = chat_module.conversation_service.process.await_args
        assert call is not None
        assert "workspace_id" not in call.args[0].metadata
