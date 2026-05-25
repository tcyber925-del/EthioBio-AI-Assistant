from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel


class DiagramLabel(SchemaModel):
    id: str
    text: str
    x: float
    y: float


class TextbookReference(SchemaModel):
    grade: int
    unit: str | None = None
    figure_number: int | None = None
    caption: str


class DiagramGenerateRequest(SchemaModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    topic: str = Field(..., pattern="^(cells|organ systems|genetics|anatomy)$")
    difficulty: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    model: Optional[str] = Field(None, min_length=1)
    grade: int = Field(default=10, ge=7, le=12)


class DiagramGenerateResponse(SchemaModel):
    diagram_svg: str
    labels: list[DiagramLabel]
    title: str
    topic: str
    difficulty: str
    model_used: str = ""
    textbook_references: list[TextbookReference] = []


class DiagramLabelResult(SchemaModel):
    label_id: str
    correct_text: str
    submitted_text: str
    is_correct: bool
    explanation: str = ""


class DiagramValidateRequest(SchemaModel):
    user_id: UUID
    correct_labels: list[DiagramLabel]
    submitted_labels: list[DiagramLabel]
    topic: str = Field(..., pattern="^(cells|organ systems|genetics|anatomy)$")
    difficulty: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")


class DiagramValidateResponse(SchemaModel):
    score: float
    total_labels: int
    correct_count: int
    results: list[DiagramLabelResult]
    attempt_id: UUID


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


class TextbookDiagramResponse(SchemaModel):
    id: UUID
    image_url: str
    caption: str
    grade_level: int
    unit: str
    topic: str
    figure_number: int
    page_number: int
    source_file: str
