from uuid import UUID

from fastapi import Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.workspace.service import WorkspaceService
from src.database.models import User, UserRole, WorkspaceMember
from src.database.session import async_session_factory


async def get_workspace_context(
    x_workspace_id: str = Header(..., alias="X-Workspace-Id"),
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> str:
    try:
        UUID(x_workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace_id format",
        )
    sf = session_factory or async_session_factory()
    service = WorkspaceService(sf)
    ws = await service.get(x_workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return x_workspace_id


async def resolve_workspace_access(
    workspace_id: str | None,
    current_user: User,
    session: AsyncSession,
) -> str | None:
    """Validate a workspace id and the caller's membership (admins bypass)."""
    if not workspace_id:
        return None
    try:
        UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace id format",
        )
    if current_user.role == UserRole.admin:
        return workspace_id
    row = (
        await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == UUID(workspace_id),
                WorkspaceMember.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this workspace",
        )
    return workspace_id
