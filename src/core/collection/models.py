from datetime import datetime

from pydantic import BaseModel


class Collection(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class NewCollection(BaseModel):
    workspace_id: str
    name: str
    description: str | None = None


class UpdateCollection(BaseModel):
    name: str | None = None
    description: str | None = None
