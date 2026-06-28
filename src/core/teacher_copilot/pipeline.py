import re

import structlog
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.quiz import QuizAgent
from src.core.teacher_copilot.evidence_engine import EvidenceEngine
from src.core.teacher_copilot.intent_router import IntentRouter
from src.core.teacher_copilot.reasoning_engine import ReasoningEngine
from src.core.teacher_copilot.state import TeacherCopilotState
from src.database.session import async_session_factory
from src.llm.router import ModelRouter

logger = structlog.get_logger()


class ClassifyIntentNode:
    def __init__(self, router: IntentRouter):
        self.router = router

    async def __call__(self, state: TeacherCopilotState) -> dict:
        intent, confidence, reasoning = await self.router.classify(state.user_message)
        return {
            "intent": intent,
            "intent_confidence": confidence,
            "intent_reasoning": reasoning,
        }


class GatherDataNode:
    def __init__(self, evidence: EvidenceEngine, session: AsyncSession | None = None):
        self.evidence = evidence
        self.session = session

    async def __call__(self, state: TeacherCopilotState) -> dict:
        session = self.session
        close_session = False
        if session is None:
            session = async_session_factory()
            close_session = True

        updates: dict = {"status": "gathered"}

        try:
            if state.user_id:
                evidence = await self.evidence.gather_evidence(
                    intent=state.intent,
                    user_id=state.user_id,
                    session=session,
                )
                updates["evidence"] = evidence
        except Exception as e:
            logger.exception("gather_evidence_error", error=str(e))
        finally:
            if close_session:
                await session.close()

        return updates


class AssessmentCreatorNode:
    def __init__(self, router: ModelRouter | None = None):
        self.llm_router = router or ModelRouter()

    async def __call__(self, state: TeacherCopilotState) -> dict:
        msg = state.user_message
        grade_match = re.search(r"grade\s*(\d+)", msg, re.IGNORECASE)
        grade_level = int(grade_match.group(1)) if grade_match else 10

        topic = "biology"
        topic_keywords = [
            "photosynthesis", "respiration", "genetics", "cell division",
            "ecology", "evolution", "classification", "circulatory",
            "digestive", "nervous", "excretory", "reproduction",
        ]
        for kw in topic_keywords:
            if kw in msg.lower():
                topic = kw.capitalize()
                break

        agent = QuizAgent(llm_router=self.llm_router)
        result = await agent.generate(
            grade_level=grade_level,
            topic=topic,
            question_count=5,
            types=["multiple_choice", "true_false"],
        )

        assessment_text = f"## {result.get('title', 'Assessment')}\n\n"
        for i, q in enumerate(result.get("questions", []), 1):
            assessment_text += f"**{i}. {q['question_text']}**\n"
            if q.get("options"):
                for opt in q["options"]:
                    assessment_text += f"   {opt}\n"
            assessment_text += "\n"

        reasoning = (
            f"I generated a {len(result.get('questions', []))}-question assessment "
            f"on **{topic}** for Grade {grade_level}. "
            f"Review the questions below or use the quiz API to save and assign them."
        )

        return {
            "reasoning": reasoning,
            "generated_assessment": result,
            "confidence": 0.85,
            "status": "assessment_created",
        }


class ReasonNode:
    def __init__(self, engine: ReasoningEngine):
        self.engine = engine

    async def __call__(self, state: TeacherCopilotState) -> dict:
        reasoning, confidence = await self.engine.reason(
            intent=state.intent,
            classroom_profile=state.classroom_profile,
            student_profiles=state.student_profiles,
            readiness_data=state.readiness_data,
            misconception_data=state.misconception_data,
            mastery_data=state.mastery_data,
            intervention_data=state.intervention_data,
            timeline_data=state.timeline_data,
            rag_context=state.rag_context,
        )
        return {
            "reasoning": reasoning,
            "confidence": confidence,
            "status": "reasoned",
        }


class FormatResponseNode:
    def __call__(self, state: TeacherCopilotState) -> dict:
        parts = [state.reasoning]

        if state.generated_assessment:
            assessment = state.generated_assessment
            questions = assessment.get("questions", [])
            parts.append("\n\n**Generated Assessment**")
            for i, q in enumerate(questions, 1):
                options_block = (
                    "".join(f"   {o}\n" for o in q.get("options", []))
                    if q.get("options") else ""
                )
                parts.append(f"\n**{i}. {q['question_text']}**\n{options_block}")
            parts.append("\n_Answer key and explanations available._")

        if state.evidence:
            from src.core.teacher_copilot.evidence_engine import EvidenceEngine
            parts.append("\n\n**Evidence:**")
            parts.append(EvidenceEngine.format_citations(state.evidence))

        response_text = "\n\n".join(parts)
        return {"response_text": response_text, "status": "complete"}


def route_after_classify(state: TeacherCopilotState) -> str:
    if state.intent == "assessment_creation":
        return "create_assessment"
    return "gather"


def build_teacher_pipeline(
    router: ModelRouter | None = None,
    session: AsyncSession | None = None,
) -> StateGraph:
    intent_router = IntentRouter()
    evidence = EvidenceEngine()
    reasoning = ReasoningEngine(router=router)

    workflow = StateGraph(TeacherCopilotState)

    workflow.add_node("classify", ClassifyIntentNode(intent_router))
    workflow.add_node("gather", GatherDataNode(evidence, session=session))
    workflow.add_node("create_assessment", AssessmentCreatorNode(router=router))
    workflow.add_node("reason", ReasonNode(reasoning))
    workflow.add_node("format", FormatResponseNode())

    workflow.set_entry_point("classify")

    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {"create_assessment": "create_assessment", "gather": "gather"},
    )

    workflow.add_edge("create_assessment", "format")
    workflow.add_edge("gather", "reason")
    workflow.add_edge("reason", "format")
    workflow.add_edge("format", END)

    return workflow
