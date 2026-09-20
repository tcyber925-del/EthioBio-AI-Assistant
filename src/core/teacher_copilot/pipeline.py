import re

import structlog
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.lesson_planner import LessonPlannerAgent
from src.agents.quiz import QuizAgent
from src.core.intervention.service import InterventionService
from src.core.learning_intelligence.teacher.teacher_service import TeacherService
from src.core.teacher_copilot.evidence_engine import EvidenceEngine
from src.core.teacher_copilot.intent_router import IntentRouter
from src.core.teacher_copilot.reasoning_engine import ReasoningEngine
from src.core.teacher_copilot.state import TeacherCopilotState
from src.database.session import async_session_factory
from src.llm.router import ModelRouter
from src.schemas.streaming import TokenChunk

logger = structlog.get_logger()

TOPIC_KEYWORDS = [
    "photosynthesis",
    "respiration",
    "genetics",
    "cell division",
    "ecology",
    "evolution",
    "classification",
    "circulatory",
    "digestive",
    "nervous",
    "excretory",
    "reproduction",
    "chemical bonding",
    "chemical reactions",
    "acids",
    "bases",
    "periodic table",
    "electrolysis",
    "motion",
    "force",
    "energy",
    "electricity",
    "magnetism",
    "waves",
    "optics",
    "algebra",
    "geometry",
    "functions",
    "equations",
    "trigonometry",
    "probability",
]


def _extract_topic(message: str) -> str:
    """Extract the subject topic from a copilot message."""
    lower = message.lower()
    for kw in TOPIC_KEYWORDS:
        if kw in lower:
            return kw.title()
    match = re.search(
        r"\b(?:about|on)\s+([a-zA-Z][a-zA-Z0-9\s'\-]{2,40}?)(?:\?|\.|$)",
        message,
        re.IGNORECASE,
    )
    if match:
        topic = match.group(1).strip()
        topic = re.sub(r"\s*(?:for\s+)?grade\s+\d+.*$", "", topic, flags=re.IGNORECASE).strip()
        if topic:
            return topic.title()
    return "Science"


async def _ground_workspace_context(workspace_id: str | None, topic: str) -> str | None:
    """Retrieve topic-relevant content from the workspace knowledge pool."""
    if not workspace_id:
        return None
    try:
        from src.core.retrieval.router import create_knowledge_router

        router = create_knowledge_router()
        results = await router.route_and_search(topic, workspace_id=workspace_id, limit=5)
        if not results:
            return None
        sections = []
        for r in results:
            best = max(r.matches, key=lambda m: m.score, default=None)
            sections.append(f"[{r.title}]\n{best.text if best else ''}")
        return "\n\n".join(sections)[:4000]
    except Exception as e:
        logger.warning("workspace_grounding_failed", error=str(e))
        return None


class ClassifyIntentNode:
    def __init__(self, router: IntentRouter):
        self.router = router

    async def __call__(self, state: TeacherCopilotState) -> dict:
        if state.token_queue:
            state.token_queue.put_nowait(
                TokenChunk(delta="Analyzing your question...", node="copilot", status=True)
            )
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
        if state.token_queue:
            state.token_queue.put_nowait(
                TokenChunk(delta="Gathering student data...", node="copilot", status=True)
            )
        session = self.session or async_session_factory()()
        close_session = self.session is None

        updates: dict = {"status": "gathered"}

        try:
            if state.classroom_id:
                try:
                    teacher = TeacherService()
                    profile = await teacher.get_classroom_overview(
                        session, state.classroom_id
                    )
                    if profile is not None:
                        updates["classroom_profile"] = profile.model_dump()
                        updates["readiness_data"] = {
                            "readiness_distribution": profile.readiness_distribution,
                            "classroom_health": profile.classroom_health,
                        }
                except Exception as e:
                    logger.warning("classroom_profile_fetch_failed", error=str(e))

                try:
                    interventions = await InterventionService().list_for_classroom(
                        str(state.classroom_id), session
                    )
                    if interventions:
                        updates["intervention_data"] = [
                            {
                                "intervention_type": i.intervention_type,
                                "topic": i.topic,
                                "status": i.status,
                                "priority": i.priority,
                                "user_id": str(i.user_id),
                            }
                            for i in interventions[:10]
                        ]
                except Exception as e:
                    logger.warning("intervention_fetch_failed", error=str(e))

            if state.user_id:
                evidence = await self.evidence.gather_evidence(
                    intent=state.intent,
                    user_id=state.user_id,
                    session=session,
                    workspace_id=state.workspace_id,
                )
                updates["evidence"] = evidence

                mastery_data = {}
                misconception_data = {}
                for e in evidence:
                    c = e["content"]
                    if e["source"] == "mastery_record":
                        mastery_data[c["topic"]] = c
                    elif e["source"] in ("memory_event", "quiz_attempt"):
                        topic = c.get("topic", c.get("quiz_id", ""))
                        misconception_data[topic] = c

                updates["mastery_data"] = mastery_data or None
                updates["misconception_data"] = misconception_data or None
            elif state.workspace_id:
                evidence = await self.evidence.gather_evidence(
                    intent=state.intent,
                    user_id=None,
                    session=session,
                    workspace_id=state.workspace_id,
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

        topic = _extract_topic(msg)

        agent = QuizAgent(llm_router=self.llm_router)

        context_override = None
        if state.workspace_id:
            context_override = await _ground_workspace_context(
                str(state.workspace_id), topic
            )

        result = await agent.generate(
            grade_level=grade_level,
            topic=topic,
            question_count=5,
            types=["multiple_choice", "true_false"],
            context_override=context_override,
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


class LessonCreatorNode:
    def __init__(self, router: ModelRouter | None = None):
        self.llm_router = router or ModelRouter()

    async def __call__(self, state: TeacherCopilotState) -> dict:
        msg = state.user_message
        grade_match = re.search(r"grade\s*(\d+)", msg, re.IGNORECASE)
        grade_level = int(grade_match.group(1)) if grade_match else 10

        topic = _extract_topic(msg)

        workspace_context = await _ground_workspace_context(
            str(state.workspace_id) if state.workspace_id else None, topic
        )

        agent = LessonPlannerAgent(llm_router=self.llm_router)
        result = await agent.generate(
            grade_level=grade_level,
            topic=topic,
            workspace_context=workspace_context,
        )

        reasoning = (
            f"I drafted a lesson plan on **{topic}** for Grade {grade_level}. "
            f"Review it below or refine it in the Lessons page."
        )

        return {
            "reasoning": reasoning,
            "generated_lesson_plan": result,
            "confidence": 0.85,
            "status": "lesson_created",
        }


class ReasonNode:
    def __init__(self, engine: ReasoningEngine):
        self.engine = engine

    async def __call__(self, state: TeacherCopilotState) -> dict:
        if state.token_queue:
            state.token_queue.put_nowait(
                TokenChunk(delta="Analyzing educational data...", node="copilot", status=True)
            )
        rag_context = EvidenceEngine.format_citations(state.evidence) if state.evidence else ""

        reasoning, confidence = await self.engine.reason(
            intent=state.intent,
            classroom_profile=state.classroom_profile,
            student_profiles=state.student_profiles or [],
            readiness_data=state.readiness_data,
            misconception_data=state.misconception_data,
            mastery_data=state.mastery_data,
            intervention_data=state.intervention_data,
            timeline_data=state.timeline_data or [],
            rag_context=rag_context,
            token_queue=state.token_queue,
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
                    "".join(f"   {o}\n" for o in q.get("options", [])) if q.get("options") else ""
                )
                parts.append(f"\n**{i}. {q['question_text']}**\n{options_block}")
            parts.append("\n_Answer key and explanations available._")

        if state.generated_lesson_plan:
            plan = state.generated_lesson_plan
            parts.append("\n\n**Generated Lesson Plan**")
            parts.append(f"\n**Objective:** {plan.get('objective', '')}")
            activities = plan.get("activities") or []
            if activities:
                parts.append("\n**Activities:**")
                for i, act in enumerate(activities[:5], 1):
                    if isinstance(act, dict):
                        parts.append(f"\n{i}. {act.get('title', act.get('name', ''))}")
            if plan.get("assessment"):
                parts.append(f"\n**Assessment:** {plan['assessment']}")
            parts.append("\n_Open the Lessons page to save or edit this plan._")

        if state.evidence:
            parts.append("\n\n**Evidence:**")
            parts.append(EvidenceEngine.format_citations(state.evidence))

        response_text = "\n\n".join(parts)
        return {"response_text": response_text, "status": "complete"}


def route_after_classify(state: TeacherCopilotState) -> str:
    if state.intent == "assessment_creation":
        return "create_assessment"
    if state.intent == "lesson_planning":
        return "create_lesson"
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
    workflow.add_node("create_lesson", LessonCreatorNode(router=router))
    workflow.add_node("reason", ReasonNode(reasoning))
    workflow.add_node("format", FormatResponseNode())

    workflow.set_entry_point("classify")

    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "create_assessment": "create_assessment",
            "create_lesson": "create_lesson",
            "gather": "gather",
        },
    )

    workflow.add_edge("create_assessment", "format")
    workflow.add_edge("create_lesson", "format")
    workflow.add_edge("gather", "reason")
    workflow.add_edge("reason", "format")
    workflow.add_edge("format", END)

    return workflow
