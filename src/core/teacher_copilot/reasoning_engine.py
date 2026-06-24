import structlog

from src.core.learning_intelligence.readiness import ReadinessService
from src.core.learning_intelligence.teacher import TeacherService
from src.llm.router import ModelRouter

logger = structlog.get_logger()


class ReasoningEngine:
    def __init__(self, router: ModelRouter | None = None):
        self.readiness = ReadinessService()
        self.teacher = TeacherService()
        self.router = router or ModelRouter()

    async def reason(
        self,
        intent: str,
        classroom_profile: dict | None = None,
        student_profiles: list[dict] | None = None,
        readiness_data: dict | None = None,
        misconception_data: dict | None = None,
        mastery_data: dict | None = None,
        intervention_data: dict | None = None,
        timeline_data: list[dict] | None = None,
        rag_context: str = "",
    ) -> tuple[str, float]:
        context_parts = []

        if classroom_profile:
            context_parts.append(f"Classroom: {classroom_profile}")
        if student_profiles:
            context_parts.append(f"Students: {student_profiles[:5]}")
        if readiness_data:
            context_parts.append(f"Readiness: {readiness_data}")
        if misconception_data:
            context_parts.append(f"Misconceptions: {misconception_data}")
        if mastery_data:
            context_parts.append(f"Mastery: {mastery_data}")
        if intervention_data:
            context_parts.append(f"Interventions: {intervention_data}")
        if timeline_data:
            context_parts.append(f"Timeline: {timeline_data[:5]}")
        if rag_context:
            context_parts.append(f"Curriculum Context: {rag_context[:500]}")

        combined_context = "\n\n".join(context_parts)

        system_prompt = (
            "You are Teacher Copilot, an educational intelligence assistant for teachers. "
            "Analyze the provided educational data and produce a clear, actionable response. "
            "Focus on: root causes, evidence-backed observations, and concrete recommendations. "
            "Keep responses concise and teacher-friendly."
        )

        user_prompt = (
            f"Intent: {intent}\n\n"
            f"Educational Data:\n{combined_context}\n\n"
            "Provide your analysis, evidence, and recommendations."
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            result = await self.router.route(
                messages=messages,
                request_type="teacher_copilot",
                temperature=0.3,
                max_tokens=1024,
            )
            reasoning = result.get("content", "Unable to generate analysis.")
            confidence = result.get("confidence", 0.7)
            return reasoning, confidence
        except Exception as e:
            logger.error("reasoning_engine_error", intent=intent, error=str(e))
            return "Unable to complete analysis due to a system error.", 0.0
