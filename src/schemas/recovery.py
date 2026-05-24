from datetime import datetime
from typing import Optional
from uuid import UUID

from src.schemas.base import SchemaModel


class RecoveryTaskResponse(SchemaModel):
    id: UUID
    plan_id: UUID
    title: str
    task_type: str
    description: Optional[str] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    xp_awarded: int = 0
    created_at: datetime


class RecoveryPlanResponse(SchemaModel):
    id: UUID
    user_id: UUID
    topic: str
    total_tasks: int
    completed_tasks: int
    status: str
    progress_pct: float = 0.0
    tasks: list[RecoveryTaskResponse] = []
    created_at: datetime
    updated_at: datetime


class RecoveryTaskCreate(SchemaModel):
    title: str
    task_type: str = "practice"
    description: Optional[str] = None


class CreateRecoveryPlanRequest(SchemaModel):
    user_id: UUID
    topic: str
    tasks: list[RecoveryTaskCreate]


class CompleteTaskResponse(SchemaModel):
    task_id: UUID
    plan_id: UUID
    xp_awarded: int = 0
    milestone_bonus: int = 0
    total_xp: int = 0
    level_up: bool = False
    new_level: int = 0
    plan_completed: bool = False
    progress_pct: float
