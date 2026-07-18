from uuid import UUID

from fastapi import Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.workspace.service import WorkspaceService
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
