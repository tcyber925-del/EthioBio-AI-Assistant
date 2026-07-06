from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


class Assignment(BaseModel):
    id: str
    workspace_id: str
    teacher_id: str
    title: str
    description: str | None = None
    instructions: str | None = None
    assignment_type: str = "homework"
    due_date: datetime | None = None
    rubric: dict = {}
    status: str = "draft"
    max_attempts: int = 1
    allow_late_submission: bool = False
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class NewAssignment(BaseModel):
    workspace_id: str
    title: str
    description: str | None = None
    instructions: str | None = None
    assignment_type: str = "homework"
    due_date: datetime | None = None
    rubric: dict = {}
    max_attempts: int = 1
    allow_late_submission: bool = False


class UpdateAssignment(BaseModel):
    title: str | None = None
    description: str | None = None
    instructions: str | None = None
    assignment_type: str | None = None
    due_date: datetime | None = None
    rubric: dict | None = None
    status: Literal["draft", "published", "completed", "archived"] | None = None
    max_attempts: int | None = None
    allow_late_submission: bool | None = None


class Submission(BaseModel):
    id: str
    assignment_id: str
    student_id: str
    storage_key: str | None = None
    content_text: str | None = None
    status: str = "submitted"
    ai_feedback: dict = {}
    teacher_feedback: dict = {}
    grade: float | None = None
    attempt_number: int = 1
    submitted_at: datetime
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class NewSubmission(BaseModel):
    storage_key: str | None = None
    content_text: str | None = None

    @model_validator(mode="after")
    def _require_content(self):
        if not self.storage_key and not self.content_text:
            raise ValueError("Either storage_key or content_text must be provided")
        return self


class UpdateSubmission(BaseModel):
    status: Literal["submitted", "under_review", "revision_requested", "reviewed", "completed"] | None = None
    ai_feedback: dict | None = None
    teacher_feedback: dict | None = None
    grade: float | None = None
