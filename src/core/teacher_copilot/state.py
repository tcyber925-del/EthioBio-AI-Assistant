from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class TeacherCopilotState:
    user_message: str = ""
    user_id: UUID | None = None
    teacher_id: UUID | None = None
    classroom_id: UUID | None = None

    intent: str = ""
    intent_confidence: float = 0.0
    intent_reasoning: str = ""

    classroom_profile: dict | None = None
    student_profiles: list[dict] = field(default_factory=list)
    readiness_data: dict | None = None
    misconception_data: dict | None = None
    mastery_data: dict | None = None
    intervention_data: dict | None = None
    timeline_data: list[dict] = field(default_factory=list)
    rag_context: str = ""

    reasoning: str = ""
    evidence: list[dict] = field(default_factory=list)
    recommendation: str = ""
    response_text: str = ""

    generated_assessment: dict | None = None

    confidence: float = 0.0
    status: str = "pending"
    error: str | None = None
