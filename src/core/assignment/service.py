from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.models import (
    Assignment as AssignmentModel,
    AssignmentStatus,
    ClassEnrollment,
    Submission as SubmissionModel,
    SubmissionStatus,
    Workspace as WorkspaceModel,
)

from .models import (
    Assignment,
    NewAssignment,
    NewSubmission,
    Submission,
    UpdateAssignment,
    UpdateSubmission,
)

logger = structlog.get_logger()


def _assignment_from_orm(row: AssignmentModel) -> Assignment:
    return Assignment(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        teacher_id=str(row.teacher_id),
        title=row.title,
        description=row.description,
        instructions=row.instructions,
        assignment_type=row.assignment_type,
        due_date=row.due_date,
        rubric=row.rubric or {},
        status=row.status.value,
        max_attempts=row.max_attempts,
        allow_late_submission=row.allow_late_submission,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


def _submission_from_orm(row: SubmissionModel) -> Submission:
    return Submission(
        id=str(row.id),
        assignment_id=str(row.assignment_id),
        student_id=str(row.student_id),
        storage_key=row.storage_key,
        content_text=row.content_text,
        status=row.status.value,
        ai_feedback=row.ai_feedback or {},
        teacher_feedback=row.teacher_feedback or {},
        grade=row.grade,
        attempt_number=row.attempt_number,
        submitted_at=row.submitted_at,
        reviewed_at=row.reviewed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class AssignmentService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create(self, data: NewAssignment, teacher_id: str) -> Assignment:
        async with self._session_factory() as db:
            row = AssignmentModel(
                workspace_id=UUID(data.workspace_id),
                teacher_id=UUID(teacher_id),
                title=data.title,
                description=data.description,
                instructions=data.instructions,
                assignment_type=data.assignment_type,
                due_date=data.due_date,
                rubric=data.rubric or {},
                max_attempts=data.max_attempts,
                allow_late_submission=data.allow_late_submission,
            )
            db.add(row)
            await db.commit()
            logger.info("assignment_created", id=str(row.id), title=data.title)
            return _assignment_from_orm(row)

    async def get(self, assignment_id: str) -> Assignment | None:
        async with self._session_factory() as db:
            row = await db.get(AssignmentModel, UUID(assignment_id))
            if row is None or row.deleted_at is not None:
                return None
            return _assignment_from_orm(row)

    async def list_for_workspace(
        self, workspace_id: str, status_filter: str | None = None
    ) -> list[Assignment]:
        async with self._session_factory() as db:
            query = (
                select(AssignmentModel)
                .where(
                    AssignmentModel.workspace_id == UUID(workspace_id),
                    AssignmentModel.deleted_at.is_(None),
                )
            )
            if status_filter:
                query = query.where(AssignmentModel.status == AssignmentStatus(status_filter))
            query = query.order_by(AssignmentModel.created_at.desc())
            rows = (await db.execute(query)).scalars().all()
            return [_assignment_from_orm(r) for r in rows]

    async def list_for_student(
        self, student_id: str, status_filter: str | None = None
    ) -> list[Assignment]:
        async with self._session_factory() as db:
            enrolled = await db.execute(
                select(ClassEnrollment).where(ClassEnrollment.student_id == UUID(student_id))
            )
            class_group_ids = [e.class_id for e in enrolled.scalars().all()]

            workspaces_query = select(WorkspaceModel).where(
                WorkspaceModel.class_group_id.in_(class_group_ids),
                WorkspaceModel.deleted_at.is_(None),
            )
            workspaces = (await db.execute(workspaces_query)).scalars().all()
            workspace_ids = [w.id for w in workspaces]

            query = (
                select(AssignmentModel)
                .where(
                    AssignmentModel.workspace_id.in_(workspace_ids),
                    AssignmentModel.deleted_at.is_(None),
                )
            )
            if status_filter:
                query = query.where(AssignmentModel.status == AssignmentStatus(status_filter))
            else:
                query = query.where(AssignmentModel.status == AssignmentStatus.published)
            query = query.order_by(AssignmentModel.due_date.asc().nullslast())
            rows = (await db.execute(query)).scalars().all()
            return [_assignment_from_orm(r) for r in rows]

    async def update(self, assignment_id: str, data: UpdateAssignment) -> Assignment | None:
        async with self._session_factory() as db:
            row = await db.get(AssignmentModel, UUID(assignment_id))
            if row is None or row.deleted_at is not None:
                return None
            if data.title is not None:
                row.title = data.title
            if data.description is not None:
                row.description = data.description
            if data.instructions is not None:
                row.instructions = data.instructions
            if data.assignment_type is not None:
                row.assignment_type = data.assignment_type
            if data.due_date is not None:
                row.due_date = data.due_date
            if data.rubric is not None:
                row.rubric = data.rubric
            if data.status is not None:
                row.status = AssignmentStatus(data.status)
            if data.max_attempts is not None:
                row.max_attempts = data.max_attempts
            if data.allow_late_submission is not None:
                row.allow_late_submission = data.allow_late_submission
            row.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("assignment_updated", id=assignment_id)
            return _assignment_from_orm(row)

    async def publish(self, assignment_id: str) -> Assignment | None:
        return await self.update(assignment_id, UpdateAssignment(status="published"))

    async def soft_delete(self, assignment_id: str) -> bool:
        async with self._session_factory() as db:
            row = await db.get(AssignmentModel, UUID(assignment_id))
            if row is None or row.deleted_at is not None:
                return False
            row.deleted_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("assignment_deleted", id=assignment_id)
            return True

    async def submit(self, assignment_id: str, student_id: str, data: NewSubmission) -> Submission | None:
        async with self._session_factory() as db:
            assignment = await db.get(AssignmentModel, UUID(assignment_id))
            if assignment is None or assignment.deleted_at is not None:
                return None

            existing = (
                await db.execute(
                    select(SubmissionModel)
                    .where(
                        SubmissionModel.assignment_id == UUID(assignment_id),
                        SubmissionModel.student_id == UUID(student_id),
                    )
                    .order_by(SubmissionModel.attempt_number.desc())
                )
            ).scalars().first()

            attempt = (existing.attempt_number + 1) if existing else 1
            if attempt > assignment.max_attempts:
                return None

            row = SubmissionModel(
                assignment_id=UUID(assignment_id),
                student_id=UUID(student_id),
                storage_key=data.storage_key,
                content_text=data.content_text,
                attempt_number=attempt,
            )
            db.add(row)
            await db.commit()
            logger.info("submission_created", id=str(row.id), assignment_id=assignment_id)
            return _submission_from_orm(row)

    async def get_submission(self, submission_id: str) -> Submission | None:
        async with self._session_factory() as db:
            row = await db.get(SubmissionModel, UUID(submission_id))
            if row is None:
                return None
            return _submission_from_orm(row)

    async def list_submissions(self, assignment_id: str) -> list[Submission]:
        async with self._session_factory() as db:
            query = (
                select(SubmissionModel)
                .where(SubmissionModel.assignment_id == UUID(assignment_id))
                .order_by(SubmissionModel.submitted_at.desc())
            )
            rows = (await db.execute(query)).scalars().all()
            return [_submission_from_orm(r) for r in rows]

    async def list_my_submissions(self, student_id: str) -> list[Submission]:
        async with self._session_factory() as db:
            query = (
                select(SubmissionModel)
                .where(SubmissionModel.student_id == UUID(student_id))
                .order_by(SubmissionModel.submitted_at.desc())
            )
            rows = (await db.execute(query)).scalars().all()
            return [_submission_from_orm(r) for r in rows]

    async def review_submission(self, submission_id: str, data: UpdateSubmission) -> Submission | None:
        async with self._session_factory() as db:
            row = await db.get(SubmissionModel, UUID(submission_id))
            if row is None:
                return None
            if data.status is not None:
                row.status = SubmissionStatus(data.status)
            if data.ai_feedback is not None:
                row.ai_feedback = data.ai_feedback
            if data.teacher_feedback is not None:
                row.teacher_feedback = data.teacher_feedback
            if data.grade is not None:
                row.grade = data.grade
            if data.status in ("reviewed", "completed"):
                row.reviewed_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("submission_reviewed", id=submission_id)
            return _submission_from_orm(row)
