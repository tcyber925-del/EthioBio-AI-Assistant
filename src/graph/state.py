"""
LangGraph state definitions for EthioBio AI Assistant.

The graph follows this sequence:
1. Classify user request
2. Decide whether retrieval is required
3. Retrieve curriculum context
4. Draft with Ollama
5. Run safety and curriculum checks
6. Revise or escalate to teacher review
7. Log the trace and outcome
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID


@dataclass
class AgentState:
    intent: str = ""
    intent_confidence: float = 0.0
    user_message: str = ""
    user_id: Optional[UUID] = None
    grade_level: Optional[int] = None
    topic: Optional[str] = None
    language: str = "en"

    retrieval_query: str = ""
    retrieved_chunks: list[dict] = field(default_factory=list)
    context: str = ""

    draft: str = ""
    model_used: str = ""
    confidence: float = 0.0
    latency_ms: int = 0

    safe: bool = True
    safety_issues: list[str] = field(default_factory=list)
    safety_score: float = 1.0

    status: str = "pending"
    requires_teacher_review: bool = False
    review_notes: str = ""

    error: Optional[str] = None
    trace_id: Optional[str] = None

    quiz_params: dict = field(default_factory=dict)
    lesson_params: dict = field(default_factory=dict)
    preferred_model: str = ""

    socratic_mode: bool = False
    guiding_question: str = ""

    hint_level: int = 0
    reveal_answer: bool = False
    misconception_detected: bool = False
    misconception_correction: str = ""


@dataclass
class GraphOutput:
    answer: str
    model_used: str
    confidence: float
    sources: list[str]
    status: str
    requires_teacher_review: bool = False
    preferred_model: str = ""
    socratic_mode: bool = False
    guiding_question: str = ""
    hint_level: int = 0
    reveal_answer: bool = False
    misconception_detected: bool = False
    misconception_correction: str = ""
