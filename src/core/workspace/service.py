from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.workspace.models import NewWorkspace, Workspace, WorkspaceMember, WorkspaceRole
from src.database.models import ClassEnrollment, ClassGroup
from src.database.models import Workspace as WorkspaceModel
from src.database.models import WorkspaceMember as WorkspaceMemberModel

logger = structlog.get_logger()


def _workspace_from_orm(row: WorkspaceModel) -> Workspace:
    return Workspace(
        id=str(row.id),
        name=row.name,
        description=row.description,
        organization_id=str(row.organization_id) if row.organization_id else None,
        class_group_id=str(row.class_group_id) if row.class_group_id else None,
        created_by=str(row.created_by),
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


def _member_from_orm(row: WorkspaceMemberModel) -> WorkspaceMember:
    return WorkspaceMember(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        user_id=str(row.user_id),
        role=row.role,
        invited_by=str(row.invited_by) if row.invited_by else None,
        joined_at=row.joined_at,
    )


class WorkspaceService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create(self, ws: NewWorkspace, created_by: str) -> Workspace:
        async with self._session_factory() as db:
            row = WorkspaceModel(
                name=ws.name,
                description=ws.description,
                organization_id=UUID(ws.organization_id) if ws.organization_id else None,
                class_group_id=UUID(ws.class_group_id) if ws.class_group_id else None,
                created_by=UUID(created_by),
            )
            db.add(row)
            await db.flush()

            db.add(
                WorkspaceMemberModel(
                    workspace_id=row.id,
                    user_id=UUID(created_by),
                    role=WorkspaceRole.owner,
                )
            )
            await db.commit()

            logger.info("workspace_created", workspace_id=str(row.id), created_by=created_by)
            return _workspace_from_orm(row)

    async def get(self, workspace_id: str) -> Workspace | None:
        async with self._session_factory() as db:
            row = await db.get(WorkspaceModel, UUID(workspace_id))
            if row is None or row.deleted_at is not None:
                return None
            return _workspace_from_orm(row)

    async def list_for_user(self, user_id: str) -> list[Workspace]:
        async with self._session_factory() as db:
            query = (
                select(WorkspaceModel)
                .join(WorkspaceMemberModel)
                .where(WorkspaceMemberModel.user_id == UUID(user_id))
                .where(WorkspaceModel.deleted_at.is_(None))
                .order_by(WorkspaceModel.created_at.desc())
            )
            rows = (await db.execute(query)).scalars().all()
            return [_workspace_from_orm(r) for r in rows]

    async def update(
        self, workspace_id: str, name: str | None = None, description: str | None = None
    ) -> Workspace | None:
        async with self._session_factory() as db:
            row = await db.get(WorkspaceModel, UUID(workspace_id))
            if row is None:
                return None
            if name is not None:
                row.name = name
            if description is not None:
                row.description = description
            row.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("workspace_updated", workspace_id=workspace_id)
            return _workspace_from_orm(row)

    async def soft_delete(self, workspace_id: str) -> bool:
        async with self._session_factory() as db:
            row = await db.get(WorkspaceModel, UUID(workspace_id))
            if row is None or row.deleted_at is not None:
                return False
            row.deleted_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("workspace_deleted", workspace_id=workspace_id)
            return True

    async def add_member(
        self,
        workspace_id: str,
        user_id: str,
        role: WorkspaceRole = WorkspaceRole.member,
        invited_by: str | None = None,
    ) -> WorkspaceMember:
        async with self._session_factory() as db:
            row = WorkspaceMemberModel(
                workspace_id=UUID(workspace_id),
                user_id=UUID(user_id),
                role=role,
                invited_by=UUID(invited_by) if invited_by else None,
            )
            db.add(row)
            try:
                await db.commit()
            except IntegrityError as e:
                await db.rollback()
                msg = str(e.orig).lower()
                if "foreign key" in msg or "violates foreign key" in msg:
                    raise ValueError(f"User {user_id} not found") from e
                raise
            logger.info(
                "workspace_member_added",
                workspace_id=workspace_id,
                user_id=user_id,
                role=role.value,
            )
            return _member_from_orm(row)

    async def remove_member(self, workspace_id: str, user_id: str) -> bool:
        async with self._session_factory() as db:
            query = select(WorkspaceMemberModel).where(
                WorkspaceMemberModel.workspace_id == UUID(workspace_id),
                WorkspaceMemberModel.user_id == UUID(user_id),
            )
            row = (await db.execute(query)).scalars().first()
            if row is None:
                return False
            await db.delete(row)
            await db.commit()
            logger.info("workspace_member_removed", workspace_id=workspace_id, user_id=user_id)
            return True

    async def list_members(self, workspace_id: str) -> list[WorkspaceMember]:
        async with self._session_factory() as db:
            query = (
                select(WorkspaceMemberModel)
                .where(WorkspaceMemberModel.workspace_id == UUID(workspace_id))
                .order_by(WorkspaceMemberModel.joined_at)
            )
            rows = (await db.execute(query)).scalars().all()
            return [_member_from_orm(r) for r in rows]

    async def update_member_role(
        self, workspace_id: str, user_id: str, role: WorkspaceRole
    ) -> bool:
        async with self._session_factory() as db:
            query = select(WorkspaceMemberModel).where(
                WorkspaceMemberModel.workspace_id == UUID(workspace_id),
                WorkspaceMemberModel.user_id == UUID(user_id),
            )
            row = (await db.execute(query)).scalars().first()
            if row is None:
                return False
            row.role = role
            await db.commit()
            logger.info(
                "workspace_member_role_updated",
                workspace_id=workspace_id,
                user_id=user_id,
                role=role.value,
            )
            return True

    async def seed_from_class_group(
        self, class_group_id: str, created_by: str | None = None
    ) -> Workspace:
        async with self._session_factory() as db:
            cg = await db.get(ClassGroup, UUID(class_group_id))
            if cg is None:
                raise ValueError(f"ClassGroup {class_group_id} not found")

            owner_id = created_by or str(cg.teacher_id)
            ws = WorkspaceModel(
                name=cg.name,
                class_group_id=cg.id,
                created_by=UUID(owner_id),
            )
            db.add(ws)
            await db.flush()

            db.add(
                WorkspaceMemberModel(
                    workspace_id=ws.id,
                    user_id=cg.teacher_id,
                    role=WorkspaceRole.owner,
                )
            )

            enroll_query = select(ClassEnrollment).where(
                ClassEnrollment.class_id == UUID(class_group_id)
            )
            enrollments = (await db.execute(enroll_query)).scalars().all()
            for enrollment in enrollments:
                db.add(
                    WorkspaceMemberModel(
                        workspace_id=ws.id,
                        user_id=enrollment.student_id,
                        role=WorkspaceRole.member,
                    )
                )

            await db.commit()
            logger.info(
                "workspace_seeded_from_class_group",
                workspace_id=str(ws.id),
                class_group_id=class_group_id,
                member_count=len(enrollments) + 1,
            )
            return _workspace_from_orm(ws)
