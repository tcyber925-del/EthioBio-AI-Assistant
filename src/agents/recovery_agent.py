import asyncio
import json
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.agents.weak_topic_detection import get_weak_topics
from src.database.models import RecoveryPlan, RecoveryTask
from src.llm.router import ModelRouter
from src.schemas.streaming import TokenChunk

logger = structlog.get_logger()

RECOVERY_SYSTEM_PROMPT = """You are EthioSci Recovery Plan Generator, creating personalized
remediation plans for Ethiopian science students (Grades 7-12) based on
their detected weak topics.

Given a student's weak topics with severity scores and misconception
patterns, generate a recovery plan with remediation tasks ordered by
priority (most critical first).

Each task must follow this JSON schema:
{{
  "title": "concise task title",
  "task_type": "review_notes" | "guided_quiz" | "diagram_exercise" |
              "retake_assessment" | "practice_questions",
  "description": "detailed description of what the student should do,
                  including specific subtopics to focus on"
}}

Task type guidance:
- review_notes: Student needs to review science notes/textbook for a specific topic
- guided_quiz: Student takes a targeted quiz on the weak area
- diagram_exercise: Student practices labeling diagrams related to the topic
- retake_assessment: Student retakes an assessment after remediation
- practice_questions: Student answers practice questions on specific subtopics

Difficulty should adapt based on severity:
- critical (score < 40%): Start with basic review and foundational concepts
- moderate (score 40-60%): Intermediate review with guided practice
- mild (score 60-80%): Focused practice and reinforcement

Output a JSON object with:
{{
  "plan_title": "Title for the recovery plan",
  "tasks": [ ... task objects ordered by priority ... ]
}}
"""


class RecoveryAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="recovery")

    async def generate_plan(
        self,
        user_id: Any,
        session: AsyncSession,
        topic_filter: Optional[str] = None,
        subject: Optional[str] = None,
        token_queue: asyncio.Queue[TokenChunk | None] | None = None,
    ) -> dict:
        weak_topics = await get_weak_topics(user_id, session)
        if not weak_topics:
            return {"plan": None, "error": "No weak topics found for this user"}

        filtered = weak_topics
        if topic_filter:
            filtered = [t for t in weak_topics if topic_filter.lower() in t["topic"].lower()]
            if not filtered:
                return {"plan": None, "error": f"No weak topics match filter: {topic_filter}"}
        if subject:
            subject_filtered = [t for t in filtered if t.get("subject") == subject]
            if subject_filtered:
                filtered = subject_filtered

        topics_summary = self._format_weak_topics(filtered)
        severity_summary = self._get_severity_summary(filtered)
        user_message = f"""Student Weak Topics:
{topics_summary}

Severity Overview: {severity_summary}

Generate a personalized recovery plan addressing these weak topics.
Order tasks so the most critical topics come first. Adapt difficulty
based on each topic's severity level.

Respond with valid JSON only."""

        if token_queue is not None:
            buf: list[str] = []
            async for token in self._call_llm_stream(
                system_prompt=RECOVERY_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.7,
                max_tokens=4096,
                request_type="recovery_plan_generation",
            ):
                buf.append(token)
                token_queue.put_nowait(TokenChunk(delta=token, node="recovery"))
            content = "".join(buf)
        else:
            result = await self._call_llm(
                system_prompt=RECOVERY_SYSTEM_PROMPT,
                user_message=user_message,
                session=session,
                temperature=0.7,
                max_tokens=4096,
                request_type="recovery_plan_generation",
            )
            content = result["content"]

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            plan_title = parsed.get("plan_title", "Personalized Recovery Plan")
            tasks = parsed.get("tasks", [])

            plan = RecoveryPlan(
                user_id=user_id,
                topic=plan_title,
                total_tasks=len(tasks),
                status="active",
            )
            session.add(plan)
            await session.flush()

            db_tasks = []
            for t in tasks:
                task = RecoveryTask(
                    plan_id=plan.id,
                    title=t.get("title", "Untitled Task"),
                    task_type=t.get("task_type", "practice_questions"),
                    description=t.get("description", ""),
                )
                session.add(task)
                db_tasks.append(task)

            await session.commit()
            await session.refresh(plan)

            if token_queue is not None:
                token_queue.put_nowait(TokenChunk(delta="", node="recovery", done=True))

            return {
                "plan": {
                    "id": str(plan.id),
                    "user_id": str(plan.user_id),
                    "topic": plan.topic,
                    "total_tasks": plan.total_tasks,
                    "status": plan.status,
                    "weak_topics_addressed": len(filtered),
                    "tasks": [
                        {
                            "id": str(t.id),
                            "title": t.title,
                            "task_type": t.task_type,
                            "description": t.description,
                        }
                        for t in db_tasks
                    ],
                    "created_at": plan.created_at.isoformat() if plan.created_at else None,
                },
                "error": None,
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(
                "recovery_plan_parse_error",
                error=str(e),
                content=result.get("content", "")[:200],
            )
            if token_queue is not None:
                token_queue.put_nowait(
                    TokenChunk(delta="", node="recovery", done=True, error=str(e))
                )
            return {"plan": None, "error": f"Failed to generate plan: {str(e)}"}

    def _format_weak_topics(self, weak_topics: list[dict]) -> str:
        lines = []
        for i, t in enumerate(weak_topics, 1):
            misconceptions = t.get("misconceptions", [])
            mc_str = ""
            if misconceptions:
                mc_list = [
                    f"- {m.get('pattern_type', '')}: {m.get('description', '')} "
                    f"(frequency: {m.get('frequency', 1)})"
                    for m in misconceptions
                ]
                mc_str = "\n    Misconceptions:\n" + "\n".join(mc_list)
            lines.append(
                f"{i}. Topic: {t['topic']}\n"
                f"   Unit: {t.get('unit', 'N/A')}\n"
                f"   Grade: {t.get('grade_level', 'N/A')}\n"
                f"   Score: {t.get('average_score', 0):.1f}%\n"
                f"   Severity: {t.get('severity', 'unknown')}\n"
                f"   Confidence: {t.get('confidence', 0):.2f}\n"
                f"   Attempts: {t.get('attempt_count', 0)}{mc_str}"
            )
        return "\n".join(lines)

    def _get_severity_summary(self, weak_topics: list[dict]) -> str:
        counts: dict[str, int] = {}
        for t in weak_topics:
            sev = t.get("severity", "unknown")
            counts[sev] = counts.get(sev, 0) + 1
        parts = [f"{count} {sev}" for sev, count in sorted(counts.items())]
        return ", ".join(parts) if parts else "No weak topics"
