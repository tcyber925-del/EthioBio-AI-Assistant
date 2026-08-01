"""
EthioBio AI Assistant — LangGraph orchestration graph.

Builds the graph with dependency-injected nodes (router, adapter).
Supports both the legacy pipeline and the new Agentic RAG pipeline.
"""

import asyncio
from collections.abc import Callable
from typing import Any, Optional

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.monitoring import pipeline_monitor
from src.graph.nodes.claim_verifier import ClaimVerifierNode, route_after_verification
from src.graph.nodes.evidence_graph import EvidenceGraphNode
from src.graph.nodes.hallucination import HallucinationNode
from src.graph.nodes.orchestrator import OrchestratorNode, needs_retrieval
from src.graph.nodes.plan_executor import PlanExecutor
from src.graph.nodes.planner import PlannerNode
from src.graph.nodes.retrieval import RetrievalNode, SkipRetrievalNode
from src.graph.nodes.safety import SafetyNode, should_revise
from src.graph.nodes.sufficient_context import SufficientContextNode, route_after_sufficiency
from src.graph.nodes.synthesis import SynthesisNode
from src.graph.nodes.tutor import TutorNode
from src.graph.state import AgentState, GraphOutput
from src.llm.router import ModelRouter
from src.retrieval.adapter import VectorStoreAdapter
from src.schemas.streaming import TokenChunk


def build_agentic_graph(
    router: ModelRouter,
    adapter: VectorStoreAdapter,
    db_session_factory: Optional[Callable[[], AsyncSession]] = None,
) -> StateGraph:
    """Build the Agentic RAG graph for complex queries.

    DEPRECATED: Use build_unified_graph() for production. This function
    is retained only for test coverage of the agentic sub-graph.

    Graph topology:
        orchestrator -> planner -> plan_executor -> evidence_graph
            -> sufficient_context -> synthesis -> tutor -> hallucination
            -> claim_verifier -> safety

    Iterative loop: If context is insufficient, routes back to plan_executor
    for retrieval iteration (max 2 iterations).
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("orchestrator", OrchestratorNode(router))
    workflow.add_node("planner", PlannerNode(router))
    workflow.add_node(
        "plan_executor",
        PlanExecutor(
            adapter,
            router=router,
            db_session_factory=db_session_factory,
        ),
    )
    workflow.add_node("evidence_graph", EvidenceGraphNode(db_session_factory=db_session_factory))
    workflow.add_node("sufficient_context", SufficientContextNode())
    workflow.add_node("synthesis", SynthesisNode(router))
    workflow.add_node("tutor", TutorNode(router))
    workflow.add_node("hallucination", HallucinationNode())
    workflow.add_node("claim_verifier", ClaimVerifierNode(router))
    workflow.add_node("safety", SafetyNode(router))

    workflow.set_entry_point("orchestrator")

    workflow.add_conditional_edges(
        "orchestrator",
        needs_retrieval,
        {"retrieve": "planner", "skip_retrieval": "safety"},
    )

    workflow.add_edge("planner", "plan_executor")
    workflow.add_edge("plan_executor", "evidence_graph")
    workflow.add_edge("evidence_graph", "sufficient_context")

    workflow.add_conditional_edges(
        "sufficient_context",
        route_after_sufficiency,
        {"synthesis": "synthesis", "rewrite": "plan_executor", "replan": "planner"},
    )

    workflow.add_edge("synthesis", "tutor")
    workflow.add_edge("tutor", "hallucination")
    workflow.add_edge("hallucination", "claim_verifier")

    workflow.add_conditional_edges(
        "claim_verifier",
        route_after_verification,
        {"finalize": "safety", "revise": "tutor", "reject": "safety"},
    )

    workflow.add_conditional_edges(
        "safety",
        should_revise,
        {"finalize": END, "revise": "tutor", "reject": END},
    )

    return workflow.compile()


async def run_graph(
    user_message: str,
    user_id: Optional[Any] = None,
    grade_level: Optional[int] = None,
    topic: Optional[str] = None,
    language: str = "en",
    preferred_model: str | None = None,
    socratic_mode: bool = False,
    hint_level: int = 0,
    reveal_answer: bool = False,
    session_id: str | None = None,
    memory_context: str = "",
    learner_profile_block: str = "",
    socratic_stage: str = "",
    socratic_focus: str = "",
    socratic_understanding: str = "",
    socratic_next_question: str = "",
    messages: list[dict] | None = None,
    db_session_factory: Optional[Callable[[], AsyncSession]] | None = None,
    token_queue: asyncio.Queue[TokenChunk | None] | None = None,
) -> GraphOutput:
    """Run the unified graph with monitoring.

    Routes to either legacy or agentic pipeline based on query complexity.
    Pass token_queue to enable streaming of LLM tokens to the caller.
    """
    trace = pipeline_monitor.start_trace(
        metadata={
            "user_id": str(user_id) if user_id else None,
            "language": language,
            "socratic_mode": socratic_mode,
        }
    )

    if token_queue:
        token_queue.put_nowait(
            TokenChunk(delta="Setting up the learning engine...", node="orchestrator", status=True)
        )

    router = ModelRouter(preferred_model=preferred_model)
    adapter = VectorStoreAdapter()

    if token_queue:
        token_queue.put_nowait(
            TokenChunk(delta="Searching the curriculum...", node="orchestrator", status=True)
        )

    # Resolve factory: callers pass src.database.session.async_session_factory
    # (a function returning async_sessionmaker). Call once to get the maker,
    # which is itself Callable[[], AsyncSession] — matching EvidenceGraphNode's
    # expected signature.
    session_maker = db_session_factory() if db_session_factory else None

    initial_state = AgentState(
        user_message=user_message,
        user_id=user_id,
        grade_level=grade_level,
        topic=topic,
        language=language,
        preferred_model=preferred_model or "",
        session_id=session_id,
        memory_context=memory_context,
        learner_profile_block=learner_profile_block,
        use_learner_awareness=bool(learner_profile_block),
        socratic_mode=socratic_mode,
        hint_level=hint_level,
        reveal_answer=reveal_answer,
        socratic_stage=socratic_stage,
        socratic_focus=socratic_focus,
        socratic_understanding=socratic_understanding,
        socratic_next_question=socratic_next_question,
        messages=messages or [],
        token_queue=token_queue,
    )

    graph = build_unified_graph(router, adapter, db_session_factory=session_maker)
    config = {"configurable": {"thread_id": f"ethiobio-{session_id or 'default'}"}}

    try:
        result = await graph.ainvoke(initial_state, config)
        metadata = {
            "user_message": initial_state.user_message,
            "response": result.get("draft", ""),
            "retrieval_iterations": result.get("retrieval_iterations", 0),
            "coverage_score": result.get("coverage_score", 0.0),
            "groundedness": result.get("groundedness_score", 0.0),
            "hallucination_rate": result.get("hallucination_rate", 0.0),
            "verdict": result.get("safety_action", ""),
            "requires_teacher_review": result.get("requires_teacher_review", False),
            "evidence_count": len(result.get("evidence_ids", [])),
        }
        await pipeline_monitor.finalize_trace(
            trace.trace_id,
            "completed",
            metadata=metadata,
        )
    except Exception as e:
        await pipeline_monitor.finalize_trace(
            trace.trace_id,
            "failed",
            metadata={"user_message": initial_state.user_message, "error": str(e)},
        )
        raise
    finally:
        await router.close()
        if token_queue:
            token_queue.put_nowait(None)

    sources = []
    for chunk in result.get("retrieved_chunks", []):
        meta = chunk.get("metadata", {})
        grade = meta.get("grade_level", "")
        unit = meta.get("unit", "")
        topic = meta.get("topic", "")
        page = meta.get("page_number", "")
        parts = []
        if grade:
            parts.append(f"Grade {grade}")
        if unit:
            parts.append(unit)
        if topic:
            parts.append(topic)
        if page:
            parts.append(f"p.{page}")
        if parts:
            sources.append(", ".join(parts))

    return GraphOutput(
        answer=result.get("draft", ""),
        model_used=result.get("model_used", ""),
        confidence=result.get("confidence", 0.0),
        sources=sources[:3],
        status=result.get("status", "pending"),
        requires_teacher_review=result.get("requires_teacher_review", False),
        session_id=result.get("session_id", ""),
        socratic_mode=result.get("socratic_mode", False),
        guiding_question=result.get("guiding_question", ""),
        socratic_stage=result.get("socratic_stage", ""),
        socratic_focus=result.get("socratic_focus", ""),
        socratic_understanding=result.get("socratic_understanding", ""),
        socratic_next_question=result.get("socratic_next_question", ""),
        hint_level=result.get("hint_level", 0),
        reveal_answer=result.get("reveal_answer", False),
        misconception_detected=result.get("misconception_detected", False),
        misconception_correction=result.get("misconception_correction", ""),
    )


def build_unified_graph(
    router: ModelRouter,
    adapter: VectorStoreAdapter,
    db_session_factory: Optional[Callable[[], AsyncSession]] = None,
) -> StateGraph:
    """Build a unified graph that handles both legacy and agentic pipelines.

    Routes based on requires_planning after the OrchestratorNode:
    - requires_planning=False: Legacy pipeline (retrieve -> tutor -> safety)
    - requires_planning=True: Agentic pipeline with iterative retrieval
    """
    workflow = StateGraph(AgentState)

    # Shared nodes
    workflow.add_node("orchestrator", OrchestratorNode(router))
    workflow.add_node("tutor", TutorNode(router))
    workflow.add_node("safety", SafetyNode(router))

    # Legacy pipeline nodes
    workflow.add_node("retrieve", RetrievalNode(adapter))
    workflow.add_node("skip_retrieval", SkipRetrievalNode(adapter))

    # Agentic pipeline nodes
    workflow.add_node("planner", PlannerNode(router))
    workflow.add_node(
        "plan_executor",
        PlanExecutor(
            adapter,
            router=router,
            db_session_factory=db_session_factory,
        ),
    )
    workflow.add_node("evidence_graph", EvidenceGraphNode(db_session_factory=db_session_factory))
    workflow.add_node("sufficient_context", SufficientContextNode())
    workflow.add_node("synthesis", SynthesisNode(router))
    workflow.add_node("hallucination", HallucinationNode())
    workflow.add_node("claim_verifier", ClaimVerifierNode(router))

    workflow.set_entry_point("orchestrator")

    # Routing from orchestrator based on requires_planning and intent
    workflow.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {
            "planner": "planner",
            "retrieve": "retrieve",
            "skip_retrieval": "skip_retrieval",
        },
    )

    # Legacy pipeline
    workflow.add_edge("retrieve", "tutor")
    workflow.add_edge("skip_retrieval", "tutor")

    # Agentic pipeline
    workflow.add_edge("planner", "plan_executor")
    workflow.add_edge("plan_executor", "evidence_graph")
    workflow.add_edge("evidence_graph", "sufficient_context")

    workflow.add_conditional_edges(
        "sufficient_context",
        route_after_sufficiency,
        {"synthesis": "synthesis", "rewrite": "plan_executor", "replan": "planner"},
    )

    # Evidence synthesis before tutor
    workflow.add_edge("synthesis", "tutor")

    # Hallucination detection then claim verification
    workflow.add_edge("tutor", "hallucination")
    workflow.add_edge("hallucination", "claim_verifier")

    workflow.add_conditional_edges(
        "claim_verifier",
        route_after_verification,
        {"finalize": "safety", "revise": "tutor", "reject": "safety"},
    )

    # Safety — conditional edge for revision loop
    workflow.add_conditional_edges(
        "safety",
        should_revise,
        {"finalize": END, "revise": "tutor", "reject": END},
    )

    return workflow.compile()


def _route_after_orchestrator(state: AgentState) -> str:
    """Route after orchestrator based on combination of requires_planning and intent.

    requires_planning is derived from complexity heuristics (subtask count,
    cross-session indicators, etc.). intent is from LLM classification.
    Both are needed: requires_planning decides if planning is needed at all,
    intent decides which pipeline to use.
    """
    # Agentic RAG: requires_planning=True AND intent supports planning
    if state.requires_planning and state.intent in ("tutor", "lesson_plan", "progress"):
        return "planner"
    # Legacy RAG: standard intents that need retrieval but not planning
    if state.intent in ("tutor", "quiz", "lesson_plan"):
        return "retrieve"
    # No retrieval needed
    return "skip_retrieval"
