import structlog
from fastapi import APIRouter, HTTPException

from src.core.workspace import NewWorkspace, WorkspaceRole, WorkspaceService
from src.core.workspace.models import Workspace, WorkspaceMember
from src.database.session import async_session_factory

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/workspaces", tags=["Workspace"])

service = WorkspaceService(async_session_factory())


@router.post("/", response_model=Workspace, status_code=201)
async def create_workspace(body: NewWorkspace):
    ws = await service.create(body, created_by=body.owner_id or "system")
    return ws


@router.get("/{workspace_id}", response_model=Workspace | None)
async def get_workspace(workspace_id: str):
    ws = await service.get(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.get("/", response_model=list[Workspace])
async def list_workspaces(user_id: str):
    return await service.list_for_user(user_id)


@router.patch("/{workspace_id}", response_model=Workspace)
async def update_workspace(
    workspace_id: str, name: str | None = None, description: str | None = None
):
    ws = await service.update(workspace_id, name=name, description=description)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(workspace_id: str):
    ok = await service.soft_delete(workspace_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Workspace not found")


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMember])
async def list_members(workspace_id: str):
    return await service.list_members(workspace_id)


@router.post("/{workspace_id}/members/{user_id}", response_model=WorkspaceMember, status_code=201)
async def add_member(workspace_id: str, user_id: str, role: WorkspaceRole = WorkspaceRole.member):
    return await service.add_member(workspace_id, user_id, role=role)


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
async def remove_member(workspace_id: str, user_id: str):
    ok = await service.remove_member(workspace_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Membership not found")


@router.patch("/{workspace_id}/members/{user_id}/role", status_code=204)
async def update_member_role(workspace_id: str, user_id: str, role: WorkspaceRole):
    ok = await service.update_member_role(workspace_id, user_id, role)
    if not ok:
        raise HTTPException(status_code=404, detail="Membership not found")


@router.post("/seed/{class_group_id}", response_model=Workspace, status_code=201)
async def seed_from_class_group(class_group_id: str):
    ws = await service.seed_from_class_group(class_group_id)
    return ws
