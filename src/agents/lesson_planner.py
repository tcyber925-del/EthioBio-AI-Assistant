import json
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()

LESSON_SYSTEM_PROMPT = (
    "You are EthioBio Lesson Planner, creating biology lesson plans "
    "for Ethiopian teachers (Grades 7-12).\n\n"
    "Output a JSON object following this schema:\n"
    "{\n"
    '  "objective": "Clear learning objective",\n'
    '  "prior_knowledge": "What students should already know",\n'
    '  "explanation": "Main lesson content and explanation",\n'
    '  "activities": [{"name": "Activity name", "duration_minutes": 10, '
    '"description": "What to do", "type": "group|individual|pair"}],\n'
    '  "periods": [\n'
    '    {\n'
    '      "name": "Opening",\n'
    '      "duration_minutes": 5,\n'
    '      "objective": "Engage students",\n'
    '      "description": "Brief warm-up activity",\n'
    '      "activity_type": "teacher_led",\n'
    '      "teacher_activity": "Pose a question",\n'
    '      "student_activity": "Discuss in pairs",\n'
    '      "materials_needed": ["Whiteboard", "Marker"]\n'
    '    }\n'
    "  ],\n"
    '  "assessment": "How to assess understanding",\n'
    '  "homework": "Optional homework assignment",\n'
    '  "teacher_notes": "Tips and preparation notes for the teacher"\n'
    "}\n\n"
    "Structure the lesson into distinct periods (Opening, Direct Instruction, "
    "Guided Practice, Independent Work, Closing) with clear time allocations. "
    "Ensure content matches the Ethiopian biology curriculum "
    "for the specified grade level."
)

MISCONCEPTION_ACTIVITY_PROMPT = (
    "You are EthioBio Misconception Remediation Specialist. "
    "Given a biology topic and specific student misconceptions, "
    "create concept conflict activities that confront and resolve them.\n\n"
    "Output a JSON array:\n"
    "[\n"
    "  {{\n"
    '    "misconception": "The misconception being addressed",\n'
    '    "activity_name": "Name of the activity",\n'
    "    \"description\": \"Step-by-step activity that creates cognitive"
    ' conflict and then resolution",\n'
    '    "duration_minutes": 10,\n'
    "    \"activity_type\": \"concept_conflict|diagnostic_question|"
    'evidence_challenge|reconstruction"\n'
    "  }}\n"
    "]"
)

DIFFERENTIATION_PROMPT = (
    "You are EthioBio Differentiation Advisor. Given a biology lesson plan, "
    "create differentiated activities for three learner groups.\n\n"
    "Output a JSON array:\n"
    "[\n"
    "  {{\n"
    '    "group": "support",\n'
    '    "description": "Simplified activity with scaffolding",\n'
    '    "duration_minutes": 10\n'
    "  }},\n"
    "  {{\n"
    '    "group": "standard",\n'
    '    "description": "Core activity at grade level",\n'
    '    "duration_minutes": 10\n'
    "  }},\n"
    "  {{\n"
    '    "group": "advanced",\n'
    '    "description": "Extended activity for deeper understanding",\n'
    '    "duration_minutes": 10\n'
    "  }}\n"
    "]"
)

DIAGRAM_SUGGESTION_PROMPT = (
    "You are EthioBio Diagram Advisor. Suggest biology diagrams that "
    "would enhance a specific lesson.\n\n"
    "Output a JSON array:\n"
    "[\n"
    "  {{\n"
    '    "title": "Diagram title",\n'
    '    "description": "What the diagram shows and how to use it",\n'
    '    "diagram_type": "flowchart|labeling|concept_map|comparison|process|anatomy"\n'
    "  }}\n"
    "]"
)

EXIT_TICKET_PROMPT = (
    "You are EthioBio Exit Ticket Generator. Create a short "
    "3-question exit ticket for a biology lesson.\n\n"
    "Output a JSON array of question objects:\n"
    "[\n"
    "  {{\n"
    '    "question_type": "multiple_choice" | "true_false" | "short_answer",\n'
    '    "question_text": "the question",\n'
    '    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],\n'
    '    "correct_answer": "the correct answer",\n'
    '    "explanation": "brief explanation"\n'
    "  }}\n"
    "]\n\n"
    "Generate 3 questions that check understanding of "
    "the key concepts from the lesson."
)


def _derive_activities_from_periods(periods: list[dict]) -> list[dict]:
    return [
        {
            "name": p.get("name", ""),
            "duration_minutes": p.get("duration_minutes", 0),
            "description": p.get("description", ""),
            "type": p.get("activity_type", "individual"),
        }
        for p in periods
    ]


class LessonPlannerAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="lesson_planner")

    async def generate(
        self,
        grade_level: int,
        topic: str,
        duration_minutes: int = 40,
        language: str = "en",
        session: Optional[AsyncSession] = None,
        generate_exit_ticket: bool = False,
        generate_differentiation: bool = False,
        generate_diagram_suggestions: bool = False,
        generate_misconception_activities: bool = False,
        classroom_context: Optional[dict] = None,
    ) -> dict:
        if language == "am":
            lang_instruction = (
                "Generate all content in Amharic (አማርኛ). "
                "Lesson plan, activities, assessment — all in Amharic."
            )
        elif language == "both":
            lang_instruction = (
                "Generate content in English with key terms "
                "and explanations also in Amharic."
            )
        else:
            lang_instruction = "Generate all content in English."

        context_block = ""
        if classroom_context:
            ctx = classroom_context
            if ctx.get("classroom"):
                c = ctx["classroom"]
                context_block = (
                    f"\n\nClassroom Context:\n"
                    f"- Total Students: {c.get('total_students', 'N/A')}\n"
                    f"- Class Health: {c.get('classroom_health', 'N/A')}%\n"
                    f"- Readiness: {c.get('readiness_distribution', {})}\n"
                    f"- Risk Students: {len(c.get('risk_students', []))}\n"
                )
            if ctx.get("misconceptions") and ctx["misconceptions"].get("by_topic"):
                context_block += "\nUnresolved Misconceptions:\n"
                for mt in ctx["misconceptions"]["by_topic"]:
                    context_block += (
                        f"- {mt['topic']}: {mt['top_pattern']} "
                        f"(affecting {mt['affected_students']} students)\n"
                    )
            if ctx.get("prerequisite_gaps"):
                context_block += "\nPrerequisite Gaps:\n"
                for pg in ctx["prerequisite_gaps"]:
                    context_block += (
                        f"- {pg['topic']}: {pg['affected_count']}/{pg['total_checked']} "
                        f"students need review\n"
                    )
            if ctx.get("best_strategies"):
                context_block += "\nRecommended Strategies:\n"
                for bs in ctx["best_strategies"]:
                    context_block += (
                        f"- {bs['type'].replace('_', ' ').title()}: "
                        f"{bs['avg_effectiveness']}% historical effectiveness\n"
                    )
            context_block += (
                "\nIncorporate this classroom intelligence into the lesson plan. "
                "Address misconceptions with concept conflict activities. "
                "Include prerequisite review where gaps exist. "
                "Use recommended teaching strategies."
            )

        user_message = f"""Create a biology lesson plan for Grade {grade_level} on topic: {topic}.
Lesson duration: {duration_minutes} minutes.
{lang_instruction}
{context_block}

Respond with valid JSON only."""

        result = await self._call_llm(
            system_prompt=LESSON_SYSTEM_PROMPT,
            user_message=user_message,
            session=session,
            temperature=0.7,
            max_tokens=4096,
            request_type="lesson_planning",
        )

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)

            raw_periods = parsed.get("periods")
            periods = (
                [p for p in raw_periods if isinstance(p, dict)]
                if isinstance(raw_periods, list)
                else None
            )
            activities = parsed.get("activities", [])
            if not isinstance(activities, list):
                activities = []
            if periods:
                activities = _derive_activities_from_periods(periods)

            output = {
                "objective": parsed.get("objective", ""),
                "prior_knowledge": parsed.get("prior_knowledge", ""),
                "explanation": parsed.get("explanation", ""),
                "activities": activities,
                "assessment": parsed.get("assessment", ""),
                "homework": parsed.get("homework"),
                "teacher_notes": parsed.get("teacher_notes"),
                "periods": periods,
                "model_used": result.get("model", ""),
            }

            if generate_exit_ticket:
                output["exit_ticket"] = await self._generate_exit_ticket(
                    grade_level=grade_level, topic=topic,
                    language=language, session=session,
                )

            if generate_differentiation:
                output["differentiation"] = await self._generate_differentiation(
                    grade_level=grade_level, topic=topic,
                    explanation=output["explanation"],
                    language=language, session=session,
                )

            if generate_diagram_suggestions:
                output["diagram_suggestions"] = await self._generate_diagram_suggestions(
                    grade_level=grade_level, topic=topic,
                    language=language, session=session,
                )

            if generate_misconception_activities and classroom_context:
                mc_list = (
                    (classroom_context.get("misconceptions") or {}).get("by_topic") or []
                )
                if mc_list:
                    output["misconception_activities"] = (
                        await self._generate_misconception_activities(
                            grade_level=grade_level,
                            topic=topic,
                            misconceptions_json=json.dumps(mc_list, indent=2),
                            language=language,
                            session=session,
                        )
                    )

            return output
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("lesson_parse_error", error=str(e), content=result["content"][:200])
            return {
                "objective": "Error parsing lesson plan",
                "prior_knowledge": "",
                "explanation": result["content"],
                "activities": [],
                "periods": None,
                "assessment": "",
                "homework": None,
                "teacher_notes": None,
                "model_used": result.get("model", ""),
            }

    async def _generate_exit_ticket(
        self,
        grade_level: int,
        topic: str,
        language: str = "en",
        session: Optional[AsyncSession] = None,
    ) -> list[dict]:
        lang_instruction = "Generate all content in English."
        if language == "am":
            lang_instruction = "Generate all content in Amharic (አማርኛ)."
        elif language == "both":
            lang_instruction = "Generate key terms in both English and Amharic."

        user_message = (
            f"Create an exit ticket for Grade {grade_level} biology lesson on {topic}.\n"
            f"{lang_instruction}\n\nRespond with valid JSON only."
        )

        return await self._call_structured(
            prompt=EXIT_TICKET_PROMPT,
            user_message=user_message,
            session=session,
            request_type="exit_ticket_generation",
        )

    async def _generate_differentiation(
        self,
        grade_level: int,
        topic: str,
        explanation: str,
        language: str = "en",
        session: Optional[AsyncSession] = None,
    ) -> list[dict]:
        lang_instruction = "Generate all content in English."
        if language == "am":
            lang_instruction = "Generate all content in Amharic."

        user_message = (
            f"Create differentiated activities for Grade {grade_level} biology lesson on {topic}.\n"
            f"Lesson explanation: {explanation[:500]}\n"
            f"{lang_instruction}\n\nRespond with valid JSON only."
        )

        return await self._call_structured(
            prompt=DIFFERENTIATION_PROMPT,
            user_message=user_message,
            session=session,
            request_type="differentiation_generation",
        )

    async def _generate_diagram_suggestions(
        self,
        grade_level: int,
        topic: str,
        language: str = "en",
        session: Optional[AsyncSession] = None,
    ) -> list[dict]:
        lang_instruction = "Generate all content in English."
        if language == "am":
            lang_instruction = "Generate all content in Amharic."

        user_message = (
            f"Suggest diagrams for Grade {grade_level} biology lesson on {topic}.\n"
            f"{lang_instruction}\n\nRespond with valid JSON only."
        )

        return await self._call_structured(
            prompt=DIAGRAM_SUGGESTION_PROMPT,
            user_message=user_message,
            session=session,
            request_type="diagram_suggestion_generation",
        )

    async def _generate_misconception_activities(
        self,
        grade_level: int,
        topic: str,
        misconceptions_json: str,
        language: str = "en",
        session: Optional[AsyncSession] = None,
    ) -> list[dict]:
        lang_instruction = "Generate all content in English."
        if language == "am":
            lang_instruction = "Generate all content in Amharic."

        user_message = (
            f"Create misconception remediation activities for Grade {grade_level} "
            f"biology lesson on {topic}.\n"
            f"Detected misconceptions:\n{misconceptions_json[:1000]}\n"
            f"{lang_instruction}\n\nRespond with valid JSON only."
        )

        return await self._call_structured(
            prompt=MISCONCEPTION_ACTIVITY_PROMPT,
            user_message=user_message,
            session=session,
            request_type="misconception_activity_generation",
        )

    async def _call_structured(
        self,
        prompt: str,
        user_message: str,
        session: Optional[AsyncSession] = None,
        request_type: str = "structured_generation",
    ) -> list[dict]:
        result = await self._call_llm(
            system_prompt=prompt,
            user_message=user_message,
            session=session,
            temperature=0.7,
            max_tokens=2048,
            request_type=request_type,
        )

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
            return parsed.get("activities") or parsed.get("suggestions") or []
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("structured_parse_error", error=str(e), content=result["content"][:200])
            return []
