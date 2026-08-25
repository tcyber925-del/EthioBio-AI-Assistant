from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import SchemaModel


class DiagramLabel(SchemaModel):
    id: str
    text: str
    x: float
    y: float


class DiagramPanel(SchemaModel):
    id: str
    caption: str
    svg: str
    labels: list[DiagramLabel]


class TextbookReference(SchemaModel):
    grade: int
    unit: str | None = None
    figure_number: int | None = None
    caption: str


class DiagramGenerateRequest(SchemaModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    topic: str = Field(..., pattern="^[a-zA-Z ]+$")
    difficulty: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    model: Optional[str] = Field(None, min_length=1)
    grade: int = Field(default=10, ge=7, le=12)
    stream: bool = False


class DiagramGenerateResponse(SchemaModel):
    diagram_svg: str
    labels: list[DiagramLabel]
    title: str
    topic: str
    difficulty: str
    model_used: str = ""
    textbook_references: list[TextbookReference] = []
    panels: list[DiagramPanel] = []


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
    topic: str = Field(..., pattern="^[a-zA-Z ]+$")
    difficulty: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    textbook_diagram_id: Optional[UUID] = None


class DiagramValidateResponse(SchemaModel):
    score: float
    total_labels: int
    correct_count: int
    results: list[DiagramLabelResult]
    attempt_id: UUID
    source: str = "ai_generated"
    xp_awarded: int = 0
    level_up: bool = False
    new_level: int = 0


class DiagramAttemptCreate(SchemaModel):
    user_id: UUID
    topic: str = Field(..., pattern="^[a-zA-Z ]+$")
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


class DiagramExportRequest(SchemaModel):
    svg: str
    title: str = "Science Diagram"
    topic: str = ""
    grade: int = 10
    labels: list[DiagramLabel] = []
    format: str = "pdf"


class SketchToDiagramResponse(SchemaModel):
    image_base64: str
    topic: str
    prompt: str
    model_used: str = ""
    width: int = 800
    height: int = 600


class AutoLabelRequest(SchemaModel):
    diagram_id: str | None = None


class AutoLabelResponse(SchemaModel):
    diagram_id: str
    caption: str
    labels_count: int
    labels: list[DiagramLabel]


class AutoLabelBatchResponse(SchemaModel):
    processed: int
    skipped: int
    results: list[AutoLabelResponse]


class ImageValidationRequest(SchemaModel):
    svg: str
    reference_image_base64: str


class ImageValidationResponse(SchemaModel):
    score: float
    mse: float = 0.0
    histogram_similarity: float = 0.0
    error: Optional[str] = None


class StyleTransferRequest(SchemaModel):
    svg: str
    reference_image_base64: str = ""
    prompt: str = "Apply textbook science diagram style, clean lines, educational formatting"


class StyleTransferResponse(SchemaModel):
    image_base64: str
    prompt: str
    width: int = 800
    height: int = 600


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
