"""
LangGraph state definitions for EthioSci.

The graph follows this sequence:
1. Classify user request
2. Decide whether retrieval is required
3. Retrieve curriculum context
4. Draft with Ollama
5. Run safety and curriculum checks
6. Revise or escalate to teacher review
7. Log the trace and outcome
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from src.schemas.streaming import TokenChunk


@dataclass
class AgentState:
    intent: str = ""
    intent_confidence: float = 0.0
    user_message: str = ""
    user_id: Optional[UUID] = None
    grade_level: Optional[int] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    language: str = "en"

    # Set by the retrieval node when a specific subject was requested but no
    # curriculum content matched (subject not yet ingested, or grade without
    # material). The tutor node uses this to return a friendly message.
    no_content_for_subject: bool = False

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

    session_id: Optional[str] = None
    memory_context: str = ""
    socratic_mode: bool = False
    guiding_question: str = ""
    socratic_stage: str = ""
    socratic_focus: str = ""
    socratic_understanding: str = ""
    socratic_next_question: str = ""

    hint_level: int = 0
    reveal_answer: bool = False
    misconception_detected: bool = False
    misconception_correction: str = ""

    learner_profile_block: str = ""
    use_learner_awareness: bool = False

    # Claim Verification
    groundedness_score: float = 0.0
    safety_action: str = ""
    safety_reason: str = ""
    ungrounded_claims: list[str] = field(default_factory=list)
    revision_count: int = 0

    # Safety revision tracking
    safety_revision_count: int = 0

    # Tool/action gating
    tool_call_history: list[dict] = field(default_factory=list)
    tool_call_count: int = 0
    step_count: int = 0

    messages: list[dict] = field(default_factory=list)

    # ============================================================
    # Agentic RAG Fields (Phase 0 — safe defaults, backward-compatible)
    # ============================================================

    # Routing
    requires_planning: bool = False

    # Planning State
    execution_plan: dict = field(default_factory=dict)
    subtasks: list[dict] = field(default_factory=list)
    complexity_score: float = 0.0

    # Query State
    rewritten_queries: list[str] = field(default_factory=list)
    query_intents: list[str] = field(default_factory=list)
    query_groups: dict[str, list[str]] = field(default_factory=dict)
    query_source_types: list[str] = field(default_factory=list)
    coverage_estimate: float = 0.0

    # Retrieval State
    retrieval_tasks: list[dict] = field(default_factory=list)
    retrieval_iterations: int = 0
    previous_evidence_count: int = 0
    retrieval_strategy: dict = field(default_factory=dict)
    retrieval_source_results: dict[str, list[dict]] = field(default_factory=dict)

    # Evidence State
    evidence_ids: list[str] = field(default_factory=list)
    evidence_items: list[dict] = field(default_factory=list)
    teaching_strategy: str = ""
    citation_map: list[dict] = field(default_factory=list)
    grounded_response: str = ""
    recommendations: list[str] = field(default_factory=list)
    hallucination_report: Optional[dict] = None
    hallucination_rate: float = 0.0
    evidence_synthesis: str = ""
    evidence_summary: str = ""
    coverage_score: float = 0.0

    # Context Sufficiency
    sufficiency_score: float = 0.0
    sufficiency_reason: str = ""
    missing_information: list[str] = field(default_factory=list)
    requires_iteration: bool = False

    # Iterative Retrieval Loop
    max_iterations: int = 3
    coverage_history: list[float] = field(default_factory=list)
    termination_reason: str = ""
    retrieval_feedback: list[str] = field(default_factory=list)

    # Learner State (snapshot added explicitly for agentic flow)
    learner_snapshot: dict = field(default_factory=dict)
    learning_recommendations: list[dict] = field(default_factory=list)
    readiness_score: float = 0.0

    # Socratic Session Caching
    socratic_session_active: bool = False
    socratic_evidence_bundle_id: Optional[str] = None

    # Streaming support
    token_queue: Optional["asyncio.Queue[TokenChunk | None]"] = None


@dataclass
class GraphOutput:
    answer: str
    model_used: str
    confidence: float
    sources: list[str]
    status: str
    requires_teacher_review: bool = False
    preferred_model: str = ""
    session_id: str = ""
    socratic_mode: bool = False
    guiding_question: str = ""
    socratic_stage: str = ""
    socratic_focus: str = ""
    socratic_understanding: str = ""
    socratic_next_question: str = ""
    hint_level: int = 0
    reveal_answer: bool = False
    misconception_detected: bool = False
    misconception_correction: str = ""
