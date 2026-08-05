from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.collection import CollectionService
from src.core.collection.models import NewCollection, UpdateCollection
from src.core.knowledge_registry import KnowledgeRegistry
from src.core.knowledge_registry.models import (
    KnowledgeFilter,
    LifecycleState,
    LifecycleTransition,
    NewKnowledgeObject,
)
from src.core.pipeline.service import PipelineOrchestrator
from src.core.storage.local import LocalFileStorage
from src.core.workspace import WorkspaceService
from src.core.workspace.models import NewWorkspace, WorkspaceRole
from src.database.models import ClassEnrollment, ClassGroup, User, UserRole
from src.database.session import Base


@pytest.fixture
def session_factory(db_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def registry(session_factory):
    return KnowledgeRegistry(session_factory)


@pytest.fixture
def workspace_service(session_factory):
    return WorkspaceService(session_factory)


@pytest.fixture
def collection_service(session_factory):
    return CollectionService(session_factory)


@pytest.fixture
def mock_embedder():
    embedder = MagicMock()

    async def embed_batch(texts, batch_size=16, use_ollama=False):
        return [[0.1] * 384 for _ in texts]

    embedder.embed_batch = embed_batch
    return embedder


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.add_documents = AsyncMock()
    return store


@pytest.fixture
def pipeline(registry, mock_embedder, mock_vector_store, session_factory):
    storage = LocalFileStorage(Path(mkdtemp()))
    return PipelineOrchestrator(
        registry=registry,
        storage=storage,
        embedder=mock_embedder,
        vector_store=mock_vector_store,
        session_factory=session_factory,
    )


@pytest.fixture
def enrichment_service(registry):
    from src.core.enrichment.service import EnrichmentService

    return EnrichmentService(registry)


class TestKnowledgeRegistry:
    async def test_register_and_get(self, registry):
        ko = NewKnowledgeObject(
            workspace_id="00000000-0000-0000-0000-000000000001",
            owner_id="00000000-0000-0000-0000-000000000002",
            title="Test Document",
            content_type="pdf",
            content_hash="abc123",
            metadata={"subject": "biology", "grade": 10},
        )
        result, events = await registry.register(ko)
        assert result.title == "Test Document"
        assert result.content_type == "pdf"
        assert result.lifecycle_state == LifecycleState.UPLOADED
        assert result.version == 1
        assert len(events) == 2
        assert events[0].event_type == "knowledge_object_registered"
        assert events[1].event_type == "version_created"

        got = await registry.get(result.id)
        assert got is not None
        assert got.title == "Test Document"

    async def test_get_nonexistent_returns_none(self, registry):
        result = await registry.get("00000000-0000-0000-0000-000000009999")
        assert result is None

    async def test_list_by_filter_workspace(self, registry):
        ws = "00000000-0000-0000-0000-000000000001"
        await registry.register(
            NewKnowledgeObject(workspace_id=ws, owner_id=ws, title="Doc1", content_type="pdf")
        )
        await registry.register(
            NewKnowledgeObject(workspace_id=ws, owner_id=ws, title="Doc2", content_type="pdf")
        )
        ws2 = "00000000-0000-0000-0000-000000000002"
        await registry.register(
            NewKnowledgeObject(workspace_id=ws2, owner_id=ws2, title="Doc3", content_type="pdf")
        )

        results = await registry.list_by_filter(KnowledgeFilter(workspace_id=ws))
        assert len(results) == 2

    async def test_lifecycle_transitions(self, registry):
        ko = NewKnowledgeObject(
            workspace_id="00000000-0000-0000-0000-000000000001",
            owner_id="00000000-0000-0000-0000-000000000002",
            title="Doc",
            content_type="pdf",
        )
        result, _ = await registry.register(ko)

        result2, events = await registry.update_lifecycle(
            result.id, LifecycleTransition(to_state=LifecycleState.PROCESSING)
        )
        assert result2.lifecycle_state == LifecycleState.PROCESSING
        assert len(events) == 1
        assert events[0].event_type == "lifecycle_changed"

        result3, events = await registry.update_lifecycle(
            result.id, LifecycleTransition(to_state=LifecycleState.PUBLISHED)
        )
        assert result3.lifecycle_state == LifecycleState.PUBLISHED

    async def test_invalid_transition_raises(self, registry):
        ko = NewKnowledgeObject(
            workspace_id="00000000-0000-0000-0000-000000000001",
            owner_id="00000000-0000-0000-0000-000000000002",
            title="Doc",
            content_type="pdf",
        )
        result, _ = await registry.register(ko)

        with pytest.raises(ValueError, match="Invalid transition"):
            await registry.update_lifecycle(
                result.id, LifecycleTransition(to_state=LifecycleState.ACTIVE)
            )

    async def test_update_metadata(self, registry):
        ko = NewKnowledgeObject(
            workspace_id="00000000-0000-0000-0000-000000000001",
            owner_id="00000000-0000-0000-0000-000000000002",
            title="Doc",
            content_type="pdf",
        )
        result, _ = await registry.register(ko)

        result2, events = await registry.update_metadata(
            result.id, {"language": "en", "difficulty": "medium"}
        )
        assert result2.metadata.get("language") == "en"
        assert result2.metadata.get("difficulty") == "medium"
        assert events[0].event_type == "metadata_updated"

    async def test_create_version(self, registry):
        ko = NewKnowledgeObject(
            workspace_id="00000000-0000-0000-0000-000000000001",
            owner_id="00000000-0000-0000-0000-000000000002",
            title="Doc",
            content_type="pdf",
        )
        result, _ = await registry.register(ko)

        version, events = await registry.create_version(result.id)
        assert version == 2
        assert events[0].event_type == "version_created"

        versions = await registry.list_versions(result.id)
        assert len(versions) == 2

    async def test_soft_delete(self, registry):
        ko = NewKnowledgeObject(
            workspace_id="00000000-0000-0000-0000-000000000001",
            owner_id="00000000-0000-0000-0000-000000000002",
            title="Doc",
            content_type="pdf",
        )
        result, _ = await registry.register(ko)

        events = await registry.soft_delete(result.id, reason="test cleanup")
        assert events[0].event_type == "knowledge_object_deleted"

        got = await registry.get(result.id)
        assert got is None

    async def test_search_by_title(self, registry):
        ws = "00000000-0000-0000-0000-000000000001"
        await registry.register(
            NewKnowledgeObject(
                workspace_id=ws, owner_id=ws, title="Cell Biology", content_type="pdf"
            )
        )
        await registry.register(
            NewKnowledgeObject(
                workspace_id=ws, owner_id=ws, title="Plant Biology", content_type="pdf"
            )
        )
        await registry.register(
            NewKnowledgeObject(
                workspace_id=ws, owner_id=ws, title="Physics 101", content_type="pdf"
            )
        )

        results = await registry.list_by_filter(KnowledgeFilter(search="Biology"))
        assert len(results) == 2


class TestLocalFileStorage:
    async def test_store_and_retrieve(self, tmp_path):
        base = Path(mkdtemp())
        storage = LocalFileStorage(base)
        src = tmp_path / "test.txt"
        src.write_text("hello world")

        key = await storage.store(src, "ws-1", "ko-1", "test.txt")
        assert "ko-1" in key
        assert "test.txt" in key

        content = await storage.retrieve(key)
        assert content.read_text() == "hello world"

    async def test_delete(self, tmp_path):
        base = Path(mkdtemp())
        storage = LocalFileStorage(base)
        src = tmp_path / "test.txt"
        src.write_text("delete me")

        key = await storage.store(src, "ws-1", "ko-2", "delete.txt")
        await storage.delete(key)

        with pytest.raises(FileNotFoundError):
            await storage.retrieve(key)

    async def test_store_nonexistent_file(self):
        base = Path(mkdtemp())
        storage = LocalFileStorage(base)
        with pytest.raises(FileNotFoundError):
            await storage.store(Path("/nonexistent/file.txt"), "ws", "ko", "f.txt")


class TestWorkspaceService:
    async def test_create_and_get(self, workspace_service):
        ws = await workspace_service.create(
            NewWorkspace(name="Test Workspace", description="A test"),
            created_by="00000000-0000-0000-0000-000000000001",
        )
        assert ws.name == "Test Workspace"
        assert ws.description == "A test"

        got = await workspace_service.get(ws.id)
        assert got is not None
        assert got.id == ws.id

    async def test_list_for_user(self, workspace_service):
        uid = "00000000-0000-0000-0000-000000000001"
        ws1 = await workspace_service.create(NewWorkspace(name="WS1"), created_by=uid)
        ws2 = await workspace_service.create(NewWorkspace(name="WS2"), created_by=uid)

        workspaces = await workspace_service.list_for_user(uid)
        assert len(workspaces) == 2
        assert ws1.id in [w.id for w in workspaces]
        assert ws2.id in [w.id for w in workspaces]

    async def test_membership(self, workspace_service):
        uid = "00000000-0000-0000-0000-000000000001"
        ws = await workspace_service.create(NewWorkspace(name="Membership Test"), created_by=uid)

        member = await workspace_service.add_member(
            ws.id,
            "00000000-0000-0000-0000-000000000002",
            role=WorkspaceRole.member,
        )
        assert member.user_id == "00000000-0000-0000-0000-000000000002"
        assert member.role == WorkspaceRole.member

        members = await workspace_service.list_members(ws.id)
        assert len(members) == 2

        ok = await workspace_service.remove_member(ws.id, "00000000-0000-0000-0000-000000000002")
        assert ok is True

        members = await workspace_service.list_members(ws.id)
        assert len(members) == 1

        not_found = await workspace_service.remove_member(
            ws.id, "00000000-0000-0000-0000-000000009999"
        )
        assert not_found is False

    async def test_update_member_role(self, workspace_service):
        uid = "00000000-0000-0000-0000-000000000001"
        ws = await workspace_service.create(NewWorkspace(name="Roles"), created_by=uid)

        ok = await workspace_service.update_member_role(ws.id, uid, WorkspaceRole.admin)
        assert ok is True

    async def test_seed_from_class_group(self, workspace_service, db_session: AsyncSession):
        teacher = User(role=UserRole.teacher)
        db_session.add(teacher)
        student1 = User(role=UserRole.student)
        db_session.add(student1)
        student2 = User(role=UserRole.student)
        db_session.add(student2)
        await db_session.flush()

        cg = ClassGroup(name="Grade 10 Biology", grade_level=10, teacher_id=teacher.id)
        db_session.add(cg)
        await db_session.flush()

        db_session.add(ClassEnrollment(class_id=cg.id, student_id=student1.id))
        db_session.add(ClassEnrollment(class_id=cg.id, student_id=student2.id))
        await db_session.commit()

        ws = await workspace_service.seed_from_class_group(str(cg.id))
        assert ws.name == "Grade 10 Biology"
        assert ws.class_group_id == str(cg.id)

        members = await workspace_service.list_members(ws.id)
        assert len(members) == 3

    async def test_soft_delete_workspace(self, workspace_service):
        ws = await workspace_service.create(
            NewWorkspace(name="To Delete"), created_by="00000000-0000-0000-0000-000000000001"
        )
        ok = await workspace_service.soft_delete(ws.id)
        assert ok is True

        got = await workspace_service.get(ws.id)
        assert got is None

    async def test_get_nonexistent(self, workspace_service):
        got = await workspace_service.get("00000000-0000-0000-0000-000000009999")
        assert got is None

    async def test_soft_delete_nonexistent(self, workspace_service):
        ok = await workspace_service.soft_delete("00000000-0000-0000-0000-000000009999")
        assert ok is False


class TestWorkspaceContext:
    async def test_valid_workspace_context(self, session_factory):
        from src.core.workspace.dependencies import get_workspace_context

        service = WorkspaceService(session_factory)
        ws = await service.create(
            NewWorkspace(name="Context Test"), created_by="00000000-0000-0000-0000-000000000001"
        )
        result = await get_workspace_context(x_workspace_id=ws.id, session_factory=session_factory)
        assert result == ws.id

    async def test_invalid_uuid_format(self):
        from fastapi import HTTPException

        from src.core.workspace.dependencies import get_workspace_context

        with pytest.raises(HTTPException) as exc:
            await get_workspace_context(x_workspace_id="not-a-uuid")
        assert exc.value.status_code == 400

    async def test_nonexistent_workspace(self, session_factory):
        from fastapi import HTTPException

        from src.core.workspace.dependencies import get_workspace_context

        with pytest.raises(HTTPException) as exc:
            await get_workspace_context(
                x_workspace_id="00000000-0000-0000-0000-000000009999",
                session_factory=session_factory,
            )
        assert exc.value.status_code == 404


@pytest.fixture
async def test_app_and_client():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    test_registry = KnowledgeRegistry(factory)
    test_storage = LocalFileStorage(Path(mkdtemp()))

    from fastapi import FastAPI

    import src.api.knowledge as knowledge_module

    knowledge_module._registry = None

    app = FastAPI()
    app.include_router(knowledge_module.router)

    _orig_get_registry = knowledge_module._get_registry
    _orig_get_storage = knowledge_module._get_storage
    _orig_get_producer = knowledge_module._get_producer
    app.dependency_overrides[_orig_get_registry] = lambda: test_registry
    app.dependency_overrides[_orig_get_storage] = lambda: test_storage
    app.dependency_overrides[_orig_get_producer] = lambda: None
    with (
        patch.object(knowledge_module, "_get_registry", return_value=test_registry),
        patch.object(knowledge_module, "_get_storage", return_value=test_storage),
        patch.object(knowledge_module, "_get_producer", return_value=None),
        patch.object(knowledge_module, "_run_pipeline_inline"),
    ):
        yield app, factory, test_storage

    await engine.dispose()


class TestKnowledgeAPI:
    async def test_upload_and_lifecycle(self, test_app_and_client):
        app, sf, storage = test_app_and_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ws_id = "00000000-0000-0000-0000-000000000001"
            owner_id = "00000000-0000-0000-0000-000000000002"

            upload_resp = await client.post(
                "/api/v1/knowledge/upload",
                files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
                params={
                    "workspace_id": ws_id,
                    "owner_id": owner_id,
                    "grade_level": 10,
                    "topic": "Cells",
                    "unit": "Biochemical Molecules",
                },
            )
            assert upload_resp.status_code == 201
            data = upload_resp.json()
            ko_id = data["id"]
            assert data["status"] == "processing"
            assert "storage_key" in data

            get_resp = await client.get(f"/api/v1/knowledge/{ko_id}")
            assert get_resp.status_code == 200
            ko = get_resp.json()
            assert ko["lifecycle_state"] == "uploaded"
            assert ko["metadata"]["grade_level"] == 10
            assert ko["metadata"]["topic"] == "Cells"
            assert ko["metadata"]["unit"] == "Biochemical Molecules"

            lifecycle_resp = await client.patch(
                f"/api/v1/knowledge/{ko_id}/lifecycle",
                json={"to_state": "processing"},
            )
            assert lifecycle_resp.status_code == 200
            assert lifecycle_resp.json()["lifecycle_state"] == "processing"

            lifecycle_resp2 = await client.patch(
                f"/api/v1/knowledge/{ko_id}/lifecycle",
                json={"to_state": "published"},
            )
            assert lifecycle_resp2.status_code == 200
            assert lifecycle_resp2.json()["lifecycle_state"] == "published"

    async def test_get_nonexistent_ko(self, test_app_and_client):
        app, sf, storage = test_app_and_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/knowledge/00000000-0000-0000-0000-000000009999")
            assert resp.status_code == 404

    async def test_soft_delete_via_api(self, test_app_and_client):
        app, sf, storage = test_app_and_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ws_id = "00000000-0000-0000-0000-000000000001"
            owner_id = "00000000-0000-0000-0000-000000000002"

            upload_resp = await client.post(
                "/api/v1/knowledge/upload",
                files={"file": ("doc.txt", b"content", "text/plain")},
                params={"workspace_id": ws_id, "owner_id": owner_id},
            )
            ko_id = upload_resp.json()["id"]

            del_resp = await client.delete(f"/api/v1/knowledge/{ko_id}")
            assert del_resp.status_code == 204

            get_resp = await client.get(f"/api/v1/knowledge/{ko_id}")
            assert get_resp.status_code == 404

    async def test_update_metadata_via_api(self, test_app_and_client):
        app, sf, storage = test_app_and_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ws_id = "00000000-0000-0000-0000-000000000001"
            owner_id = "00000000-0000-0000-0000-000000000002"

            upload_resp = await client.post(
                "/api/v1/knowledge/upload",
                files={"file": ("meta.txt", b"meta", "text/plain")},
                params={"workspace_id": ws_id, "owner_id": owner_id},
            )
            ko_id = upload_resp.json()["id"]

            meta_resp = await client.patch(
                f"/api/v1/knowledge/{ko_id}/metadata",
                json={"language": "en", "difficulty": "hard"},
            )
            assert meta_resp.status_code == 200
            assert meta_resp.json()["metadata"]["language"] == "en"
            assert meta_resp.json()["metadata"]["difficulty"] == "hard"

    async def test_download_knowledge_object(self, test_app_and_client):
        app, sf, storage = test_app_and_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ws_id = "00000000-0000-0000-0000-000000000001"
            owner_id = "00000000-0000-0000-0000-000000000002"

            upload_resp = await client.post(
                "/api/v1/knowledge/upload",
                files={"file": ("download.txt", b"hello world content", "text/plain")},
                params={"workspace_id": ws_id, "owner_id": owner_id},
            )
            assert upload_resp.status_code == 201
            ko_id = upload_resp.json()["id"]

            download_resp = await client.get(f"/api/v1/knowledge/{ko_id}/download")
            assert download_resp.status_code == 200

    async def test_create_and_list_versions_via_api(self, test_app_and_client):
        app, sf, storage = test_app_and_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ws_id = "00000000-0000-0000-0000-000000000001"
            owner_id = "00000000-0000-0000-0000-000000000002"

            upload_resp = await client.post(
                "/api/v1/knowledge/upload",
                files={"file": ("v1.txt", b"v1", "text/plain")},
                params={"workspace_id": ws_id, "owner_id": owner_id},
            )
            ko_id = upload_resp.json()["id"]

            ver_resp = await client.post(f"/api/v1/knowledge/{ko_id}/versions")
            assert ver_resp.status_code == 200
            assert ver_resp.json()["version"] == 2

            list_resp = await client.get(f"/api/v1/knowledge/{ko_id}/versions")
            assert list_resp.status_code == 200
            assert len(list_resp.json()) == 2


class TestCollection:
    async def test_create_and_get(self, collection_service):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        coll = await collection_service.create(
            NewCollection(workspace_id=ws_id, name="Biology Notes", description="Grade 10 biology"),
            created_by=owner_id,
        )
        assert coll.name == "Biology Notes"
        assert coll.description == "Grade 10 biology"
        assert coll.workspace_id == ws_id

        got = await collection_service.get(coll.id)
        assert got is not None
        assert got.name == "Biology Notes"

    async def test_get_nonexistent(self, collection_service):
        result = await collection_service.get("00000000-0000-0000-0000-000000009999")
        assert result is None

    async def test_list_for_workspace(self, collection_service):
        ws_id = "00000000-0000-0000-0000-000000000001"
        ws2_id = "00000000-0000-0000-0000-000000000002"
        owner_id = "00000000-0000-0000-0000-000000000003"

        await collection_service.create(
            NewCollection(workspace_id=ws_id, name="C1"), created_by=owner_id
        )
        await collection_service.create(
            NewCollection(workspace_id=ws_id, name="C2"), created_by=owner_id
        )
        await collection_service.create(
            NewCollection(workspace_id=ws2_id, name="C3"), created_by=owner_id
        )

        cols = await collection_service.list_for_workspace(ws_id)
        assert len(cols) == 2

    async def test_update(self, collection_service):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        coll = await collection_service.create(
            NewCollection(workspace_id=ws_id, name="Original"), created_by=owner_id
        )
        updated = await collection_service.update(
            coll.id, UpdateCollection(name="Renamed", description="Updated desc")
        )
        assert updated is not None
        assert updated.name == "Renamed"
        assert updated.description == "Updated desc"

    async def test_soft_delete(self, collection_service):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        coll = await collection_service.create(
            NewCollection(workspace_id=ws_id, name="To Delete"), created_by=owner_id
        )
        ok = await collection_service.soft_delete(coll.id)
        assert ok is True

        got = await collection_service.get(coll.id)
        assert got is None

    async def test_add_and_remove_knowledge_object(
        self, collection_service, session_factory, registry
    ):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        coll = await collection_service.create(
            NewCollection(workspace_id=ws_id, name="My Collection"), created_by=owner_id
        )
        ko, _ = await registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id, owner_id=owner_id, title="Doc", content_type="pdf"
            )
        )

        ok = await collection_service.add_knowledge_object(coll.id, ko.id)
        assert ok is True

        items = await collection_service.list_knowledge_objects(coll.id)
        assert len(items) == 1
        assert items[0].id == ko.id

        ok = await collection_service.remove_knowledge_object(coll.id, ko.id)
        assert ok is True

        items = await collection_service.list_knowledge_objects(coll.id)
        assert len(items) == 0

    async def test_add_to_nonexistent_collection(self, collection_service, registry):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        ko, _ = await registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id, owner_id=owner_id, title="Doc", content_type="pdf"
            )
        )

        ok = await collection_service.add_knowledge_object(
            "00000000-0000-0000-0000-000000009999", ko.id
        )
        assert ok is False


class TestSearch:
    async def test_search_returns_matching_ko(self, test_app_and_client):
        app, sf, storage = test_app_and_client

        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        test_registry = KnowledgeRegistry(sf)
        ko, _ = await test_registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id,
                owner_id=owner_id,
                title="Cell Biology Textbook",
                content_type="pdf",
            )
        )
        await test_registry.update_lifecycle(
            ko.id, LifecycleTransition(to_state=LifecycleState.PROCESSING)
        )
        await test_registry.update_lifecycle(
            ko.id, LifecycleTransition(to_state=LifecycleState.PUBLISHED)
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            import src.api.knowledge as knowledge_module
            from src.core.retrieval.models import RetrievalResult, TextMatch

            mock_gateway = MagicMock()
            mock_gateway.search = AsyncMock(
                return_value=[
                    RetrievalResult(
                        ko_id=ko.id,
                        title="Cell Biology Textbook",
                        content_type="pdf",
                        score=0.85,
                        matches=[
                            TextMatch(
                                text="Cells are the basic unit of life", chunk_index=0, score=0.85
                            ),
                            TextMatch(
                                text="DNA contains genetic information", chunk_index=1, score=0.75
                            ),
                        ],
                    ),
                ]
            )

            with patch.object(knowledge_module, "_get_gateway", return_value=mock_gateway):
                resp = await client.get(
                    "/api/v1/knowledge/search",
                    params={"q": "cell biology", "workspace_id": ws_id, "limit": 5},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["ko_id"] == ko.id
            assert data[0]["title"] == "Cell Biology Textbook"
            assert len(data[0]["matches"]) == 2
            assert data[0]["matches"][0]["text"] == "Cells are the basic unit of life"

    async def test_search_returns_empty_for_nonexistent_ko(self, test_app_and_client):
        app, sf, storage = test_app_and_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            import src.api.knowledge as knowledge_module

            mock_gateway = MagicMock()
            mock_gateway.search = AsyncMock(return_value=[])

            with patch.object(knowledge_module, "_get_gateway", return_value=mock_gateway):
                resp = await client.get("/api/v1/knowledge/search", params={"q": "anything"})
            assert resp.status_code == 200
            assert resp.json() == []

    async def test_search_requires_query(self, test_app_and_client):
        app, sf, storage = test_app_and_client

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/knowledge/search")
            assert resp.status_code == 422


class TestPipeline:
    async def test_successful_pipeline_run(self, pipeline, tmp_path):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        ko, _ = await pipeline._registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id, owner_id=owner_id, title="Pipeline Test", content_type="txt"
            )
        )

        file_path = tmp_path / "test.txt"
        file_path.write_text(
            "First paragraph about biology.\n\nSecond paragraph about cells.\n\nThird paragraph about DNA."
        )
        result = await pipeline.run(ko.id, file_path)

        assert result.success is True
        assert result.error is None

        updated = await pipeline._registry.get(ko.id)
        assert updated is not None
        assert updated.lifecycle_state == LifecycleState.PUBLISHED
        assert updated.metadata.get("chunk_count") == 3

        import json

        enrichment_raw = updated.metadata.get("enrichment")
        assert enrichment_raw is not None
        enrichment = json.loads(enrichment_raw)
        assert enrichment["ko_id"] == ko.id
        assert enrichment["word_count"] > 0
        assert len(enrichment["key_terms"]) > 0
        assert enrichment["excerpt"] is not None

    async def test_validation_rejects_unsupported_format(self, pipeline, tmp_path):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        ko, _ = await pipeline._registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id,
                owner_id=owner_id,
                title="Bad Format",
                content_type="application/octet-stream",
            )
        )

        file_path = tmp_path / "bad.exe"
        file_path.write_bytes(b"\x00\x01\x02")
        result = await pipeline.run(ko.id, file_path)

        assert result.success is False
        assert result.stage == "validation"
        assert "Unsupported file format" in result.error

        updated = await pipeline._registry.get(ko.id)
        assert updated is not None
        assert updated.lifecycle_state == LifecycleState.FAILED

    async def test_validation_rejects_oversized_file(self, pipeline, tmp_path):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        ko, _ = await pipeline._registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id, owner_id=owner_id, title="Big File", content_type="txt"
            )
        )

        file_path = tmp_path / "big.txt"
        file_path.write_bytes(b"x" * (60 * 1024 * 1024))
        result = await pipeline.run(ko.id, file_path, max_file_size_mb=50)

        assert result.success is False
        assert result.stage == "validation"
        assert "exceeds" in result.error

    async def test_validation_rejects_duplicate_content(self, pipeline, tmp_path, session_factory):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        file_path = tmp_path / "dup.txt"
        import hashlib

        content = b"same content"
        file_path.write_bytes(content)
        actual_hash = hashlib.sha256(content).hexdigest()

        existing, _ = await pipeline._registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id,
                owner_id=owner_id,
                title="Existing",
                content_type="txt",
                content_hash=actual_hash,
            )
        )
        await pipeline._registry.update_lifecycle(
            existing.id, LifecycleTransition(to_state=LifecycleState.PROCESSING)
        )
        await pipeline._registry.update_lifecycle(
            existing.id, LifecycleTransition(to_state=LifecycleState.PUBLISHED)
        )

        duplicate, _ = await pipeline._registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id,
                owner_id=owner_id,
                title="Duplicate",
                content_type="txt",
            )
        )

        result = await pipeline.run(duplicate.id, file_path)
        assert result.success is False
        assert result.stage == "validation"
        assert "Duplicate" in result.error

    async def test_skips_vector_store_when_not_configured(
        self, registry, tmp_path, session_factory
    ):
        storage = LocalFileStorage(Path(mkdtemp()))
        no_store_pipeline = PipelineOrchestrator(
            registry=registry,
            storage=storage,
            embedder=MagicMock(),
            vector_store=None,
            session_factory=session_factory,
        )

        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        ko, _ = await registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id, owner_id=owner_id, title="No Vec", content_type="txt"
            )
        )

        file_path = tmp_path / "simple.txt"
        file_path.write_text("Simple content for testing without vector store.")
        result = await no_store_pipeline.run(ko.id, file_path)

        assert result.success is True
        updated = await registry.get(ko.id)
        assert updated is not None
        assert updated.lifecycle_state == LifecycleState.PUBLISHED

    async def test_pdf_extraction_and_chunking(self, pipeline, tmp_path):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        ko, _ = await pipeline._registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id, owner_id=owner_id, title="PDF Test", content_type="pdf"
            )
        )

        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.add_blank_page(width=612, height=792)
        file_path = tmp_path / "test.pdf"
        with open(file_path, "wb") as f:
            writer.write(f)

        result = await pipeline.run(ko.id, file_path)
        assert result.success is True

        updated = await pipeline._registry.get(ko.id)
        assert updated is not None
        assert updated.lifecycle_state == LifecycleState.PUBLISHED

    async def test_pipeline_handles_empty_file(self, pipeline, tmp_path):
        ws_id = "00000000-0000-0000-0000-000000000001"
        owner_id = "00000000-0000-0000-0000-000000000002"

        ko, _ = await pipeline._registry.register(
            NewKnowledgeObject(
                workspace_id=ws_id, owner_id=owner_id, title="Empty", content_type="txt"
            )
        )

        file_path = tmp_path / "empty.txt"
        file_path.write_text("")
        result = await pipeline.run(ko.id, file_path)

        assert result.success is True
        updated = await pipeline._registry.get(ko.id)
        assert updated is not None
        assert updated.lifecycle_state == LifecycleState.PUBLISHED
        assert updated.metadata.get("chunk_count") == 0


class TestEnrichment:
    async def test_extract_key_terms(self, enrichment_service):
        text = "biology biology biology cell cell dna genetics"
        terms = enrichment_service._extract_key_terms(text, max_terms=10, min_freq=1, min_length=1)
        assert "biology" in terms
        assert "cell" in terms
        assert "dna" in terms
        assert "genetics" in terms
        assert terms.index("biology") < terms.index("cell")

    async def test_extract_key_terms_excludes_stopwords(self, enrichment_service):
        text = "the the and and for biology cell with is"
        terms = enrichment_service._extract_key_terms(text, max_terms=10, min_freq=1, min_length=1)
        assert "biology" in terms
        assert "cell" in terms
        assert "the" not in terms
        assert "and" not in terms
        assert "for" not in terms
        assert "with" not in terms
        assert "is" not in terms

    async def test_extract_key_terms_min_freq_filter(self, enrichment_service):
        text = "biology cell cell dna dna dna"
        terms = enrichment_service._extract_key_terms(text, max_terms=10, min_freq=2)
        assert "biology" not in terms
        assert "cell" in terms
        assert "dna" in terms

    async def test_extract_excerpt_short_text(self, enrichment_service):
        text = "Short text about biology."
        excerpt, source = enrichment_service._extract_excerpt(text, max_chars=500)
        assert excerpt == "Short text about biology."
        assert source == "full_text"

    async def test_extract_excerpt_long_text(self, enrichment_service):
        text = "A" * 1000
        excerpt, source = enrichment_service._extract_excerpt(text, max_chars=500)
        assert source == "truncated"
        assert excerpt is not None
        assert len(excerpt) <= 500 + 3
        assert excerpt.endswith("...")

    async def test_classify_lesson(self, enrichment_service):
        text = "This lesson covers the learning outcomes for cell biology. Students will understand mitosis."
        cls = enrichment_service._classify_content(text, "text/plain")
        assert cls == "lesson"

    async def test_classify_assessment(self, enrichment_service):
        text = "Multiple choice questions for the exam. Answer all questions."
        cls = enrichment_service._classify_content(text, "text/plain")
        assert cls == "assessment"

    async def test_classify_fallback_by_mime(self, enrichment_service):
        cls = enrichment_service._classify_content("random text", "application/pdf")
        assert cls == "document"

    async def test_classify_none_when_unknown(self, enrichment_service):
        cls = enrichment_service._classify_content("random text", "application/octet-stream")
        assert cls is None

    async def test_full_enrichment_flow(self, enrichment_service, registry):
        ko, _ = await registry.register(
            NewKnowledgeObject(
                workspace_id="00000000-0000-0000-0000-000000000001",
                owner_id="00000000-0000-0000-0000-000000000002",
                title="Enrichment Test",
                content_type="txt",
            )
        )
        chunks = [
            "This lesson covers the learning outcomes for biology biology.",
            "Students will understand cell structure, DNA, and genetics genetics.",
            "Key topics include cell division, mitosis, and meiosis.",
        ]
        result = await enrichment_service.enrich(ko.id, chunks, "text/plain")
        assert result.ko_id == ko.id
        assert result.word_count > 0
        assert "biology" in result.key_terms
        assert "cell" in result.key_terms
        assert "genetics" in result.key_terms
        assert result.content_class == "lesson"
        assert result.excerpt is not None
        assert result.chunk_count == 3

    async def test_enrichment_empty_chunks(self, enrichment_service, registry):
        ko, _ = await registry.register(
            NewKnowledgeObject(
                workspace_id="00000000-0000-0000-0000-000000000001",
                owner_id="00000000-0000-0000-0000-000000000002",
                title="Empty Enrichment",
                content_type="txt",
            )
        )
        result = await enrichment_service.enrich(ko.id, [], "text/plain")
        assert result.word_count == 0
        assert result.key_terms == []
        assert result.chunk_count == 0

    async def test_enrichment_endpoint_returns_enrichment(self, test_app_and_client):
        app, sf, storage = test_app_and_client
        app_registry = KnowledgeRegistry(sf)

        ko, _ = await app_registry.register(
            NewKnowledgeObject(
                workspace_id="00000000-0000-0000-0000-000000000001",
                owner_id="00000000-0000-0000-0000-000000000002",
                title="Enrich API Test",
                content_type="txt",
            )
        )

        from src.core.enrichment.service import EnrichmentService

        enricher = EnrichmentService(app_registry)
        await enricher.enrich(ko.id, ["biology biology cell dna dna"], "text/plain")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/knowledge/{ko.id}/enrichment")
            assert resp.status_code == 200
            data = resp.json()
            assert data["enriched"] is True
            assert data["word_count"] > 0
            assert len(data["key_terms"]) > 0

    async def test_enrichment_stores_metadata(self, enrichment_service, registry):
        ko, _ = await registry.register(
            NewKnowledgeObject(
                workspace_id="00000000-0000-0000-0000-000000000001",
                owner_id="00000000-0000-0000-0000-000000000002",
                title="Metadata Store Test",
                content_type="txt",
            )
        )
        chunks = ["biology cell dna genetics"]
        await enrichment_service.enrich(ko.id, chunks, "text/plain")
        updated = await registry.get(ko.id)
        assert updated is not None
        assert "enrichment" in updated.metadata
        import json

        stored = json.loads(updated.metadata["enrichment"])
        assert stored["ko_id"] == ko.id
        assert stored["enrichment_version"] == "1"
