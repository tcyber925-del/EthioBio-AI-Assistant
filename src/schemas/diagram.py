from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel


class DiagramAttemptCreate(SchemaModel):
    user_id: UUID
    topic: str = Field(..., pattern="^(cells|organ systems|genetics|anatomy)$")
    difficulty: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")


class DiagramAttemptResponse(SchemaModel):
    id: UUID
    user_id: UUID
    topic: str
    difficulty: str
    score: Optional[float] = None
    labels: dict = {}
    completed: bool = False
    started_at: str
    completed_at: Optional[str] = None
