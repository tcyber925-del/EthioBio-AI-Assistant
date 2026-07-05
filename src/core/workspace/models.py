from datetime import datetime

from pydantic import BaseModel

from src.database.models import WorkspaceRole


class Workspace(BaseModel):
    id: str
    name: str
    description: str | None
    organization_id: str | None
    class_group_id: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class NewWorkspace(BaseModel):
    name: str
    description: str | None = None
    organization_id: str | None = None
    class_group_id: str | None = None
    owner_id: str | None = None


class WorkspaceMember(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    invited_by: str | None
    joined_at: datetime
