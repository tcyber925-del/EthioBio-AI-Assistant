"""
EthioBio AI Assistant — LangGraph orchestration graph.

Builds the graph with dependency-injected nodes (router, adapter).
"""

from langgraph.graph import END, StateGraph

from src.graph.nodes.orchestrator import OrchestratorNode, needs_retrieval
from src.graph.nodes.retrieval import RetrievalNode, SkipRetrievalNode
from src.graph.nodes.safety import SafetyNode, should_revise
from src.graph.nodes.tutor import TutorNode
from src.graph.state import AgentState, GraphOutput
from src.llm.router import ModelRouter
from src.retrieval.adapter import VectorStoreAdapter


def build_graph(router: ModelRouter, adapter: VectorStoreAdapter) -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("orchestrator", OrchestratorNode(router))
    workflow.add_node("retrieve", RetrievalNode(adapter))
    workflow.add_node("skip_retrieval", SkipRetrievalNode(adapter))
    workflow.add_node("tutor", TutorNode(router))
    workflow.add_node("safety", SafetyNode(router))

    workflow.set_entry_point("orchestrator")

    workflow.add_conditional_edges(
        "orchestrator",
        needs_retrieval,
        {"retrieve": "retrieve", "skip_retrieval": "skip_retrieval"},
    )

    workflow.add_edge("retrieve", "tutor")
    workflow.add_edge("skip_retrieval", "tutor")
    workflow.add_edge("tutor", "safety")

    workflow.add_conditional_edges(
        "safety",
        should_revise,
        {"revise": "tutor", "reject": "tutor", "finalize": END},
    )

    return workflow.compile()


async def run_graph(
    user_message: str,
    user_id=None,
    grade_level: int = None,
    topic: str = None,
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
) -> GraphOutput:
    router = ModelRouter(preferred_model=preferred_model)
    adapter = VectorStoreAdapter()

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
    )

    graph = build_graph(router, adapter)
    config = {"configurable": {"thread_id": "ethiobio-run-1"}}

    try:
        result = await graph.ainvoke(initial_state, config)
    finally:
        await router.close()

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
