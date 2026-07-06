import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.assignment import AssignmentService
from src.core.assignment.models import NewAssignment, NewSubmission, UpdateAssignment, UpdateSubmission
from src.database.models import (
    Assignment as AssignmentModel,
    ClassEnrollment,
    ClassGroup,
    Submission as SubmissionModel,
    User,
    UserRole,
    Workspace as WorkspaceModel,
)
from src.database.session import Base


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def session_factory(db_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(db_session.bind, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def service(session_factory):
    return AssignmentService(session_factory)


@pytest.fixture
async def teacher_user(db_session: AsyncSession):
    row = User(id=uuid.uuid4(), telegram_id=999001, role=UserRole.teacher)
    db_session.add(row)
    await db_session.commit()
    return str(row.id)


@pytest.fixture
async def student_user(db_session: AsyncSession):
    row = User(id=uuid.uuid4(), telegram_id=999002, role=UserRole.student)
    db_session.add(row)
    await db_session.commit()
    return str(row.id)


@pytest.fixture
async def workspace(db_session: AsyncSession, teacher_user: str):
    row = WorkspaceModel(
        id=uuid.uuid4(),
        name="Test Classroom",
        created_by=uuid.UUID(teacher_user),
    )
    db_session.add(row)
    await db_session.commit()
    return str(row.id)


@pytest.fixture
async def class_group(db_session: AsyncSession, teacher_user: str, student_user: str):
    cg = ClassGroup(id=uuid.uuid4(), name="Grade 10-A", grade_level=10, teacher_id=uuid.UUID(teacher_user))
    db_session.add(cg)
    await db_session.commit()

    enrollment = ClassEnrollment(
        id=uuid.uuid4(),
        class_id=cg.id,
        student_id=uuid.UUID(student_user),
    )
    db_session.add(enrollment)
    await db_session.commit()
    return str(cg.id)


@pytest.fixture
async def class_workspace(db_session: AsyncSession, teacher_user: str, class_group: str):
    row = WorkspaceModel(
        id=uuid.uuid4(),
        name="Grade 10-A Workspace",
        class_group_id=uuid.UUID(class_group),
        created_by=uuid.UUID(teacher_user),
    )
    db_session.add(row)
    await db_session.commit()
    return str(row.id)


class TestAssignmentService:
    async def test_create(self, service, workspace, teacher_user):
        data = NewAssignment(
            workspace_id=workspace,
            title="Cell Division Homework",
            description="Chapter 3 review",
            assignment_type="homework",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        result = await service.create(data, teacher_user)
        assert result.title == "Cell Division Homework"
        assert result.status == "draft"
        assert result.workspace_id == workspace
        assert result.teacher_id == teacher_user

    async def test_get(self, service, workspace, teacher_user):
        data = NewAssignment(workspace_id=workspace, title="Test")
        created = await service.create(data, teacher_user)
        result = await service.get(created.id)
        assert result is not None
        assert result.id == created.id

    async def test_get_not_found(self, service):
        result = await service.get(str(uuid.uuid4()))
        assert result is None

    async def test_list_for_workspace(self, service, workspace, teacher_user):
        await service.create(NewAssignment(workspace_id=workspace, title="A1"), teacher_user)
        await service.create(NewAssignment(workspace_id=workspace, title="A2"), teacher_user)
        results = await service.list_for_workspace(workspace)
        assert len(results) == 2

    async def test_update(self, service, workspace, teacher_user):
        created = await service.create(NewAssignment(workspace_id=workspace, title="Original"), teacher_user)
        updated = await service.update(created.id, UpdateAssignment(title="Updated"))
        assert updated is not None
        assert updated.title == "Updated"

    async def test_publish(self, service, workspace, teacher_user):
        created = await service.create(NewAssignment(workspace_id=workspace, title="To Publish"), teacher_user)
        published = await service.publish(created.id)
        assert published is not None
        assert published.status == "published"

    async def test_soft_delete(self, service, workspace, teacher_user):
        created = await service.create(NewAssignment(workspace_id=workspace, title="To Delete"), teacher_user)
        ok = await service.soft_delete(created.id)
        assert ok is True
        result = await service.get(created.id)
        assert result is None

    async def test_submit_and_list(self, service, workspace, teacher_user, student_user):
        created = await service.create(NewAssignment(workspace_id=workspace, title="Submit Test"), teacher_user)
        await service.publish(created.id)

        sub = await service.submit(
            created.id, student_user, NewSubmission(content_text="My homework answer")
        )
        assert sub is not None
        assert sub.assignment_id == created.id
        assert sub.student_id == student_user
        assert sub.status == "submitted"
        assert sub.attempt_number == 1

        submissions = await service.list_submissions(created.id)
        assert len(submissions) == 1

    async def test_submit_exceeds_max_attempts(self, service, workspace, teacher_user, student_user):
        created = await service.create(
            NewAssignment(workspace_id=workspace, title="Limited Attempts", max_attempts=1),
            teacher_user,
        )
        await service.publish(created.id)

        sub1 = await service.submit(created.id, student_user, NewSubmission(content_text="Attempt 1"))
        assert sub1 is not None

        sub2 = await service.submit(created.id, student_user, NewSubmission(content_text="Attempt 2"))
        assert sub2 is None

    async def test_review_submission(self, service, workspace, teacher_user, student_user):
        created = await service.create(NewAssignment(workspace_id=workspace, title="Review Test"), teacher_user)
        await service.publish(created.id)
        sub = await service.submit(created.id, student_user, NewSubmission(content_text="Answer"))

        reviewed = await service.review_submission(
            sub.id, UpdateSubmission(status="reviewed", grade=85.0, teacher_feedback={"comment": "Good work"})
        )
        assert reviewed is not None
        assert reviewed.status == "reviewed"
        assert reviewed.grade == 85.0
        assert reviewed.teacher_feedback["comment"] == "Good work"
        assert reviewed.reviewed_at is not None

    async def test_my_submissions(self, service, workspace, teacher_user, student_user):
        created = await service.create(NewAssignment(workspace_id=workspace, title="My Sub"), teacher_user)
        await service.publish(created.id)
        await service.submit(created.id, student_user, NewSubmission(content_text="My answer"))

        results = await service.list_my_submissions(student_user)
        assert len(results) == 1
        assert results[0].student_id == student_user

    async def test_list_for_student(self, service, class_workspace, teacher_user, student_user):
        created = await service.create(
            NewAssignment(workspace_id=class_workspace, title="Student Assignment"),
            teacher_user,
        )
        await service.publish(created.id)

        results = await service.list_for_student(student_user)
        assert len(results) >= 1
        assert any(a.id == created.id for a in results)
