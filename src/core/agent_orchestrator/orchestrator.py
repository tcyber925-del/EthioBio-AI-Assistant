from __future__ import annotations

import time
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agent_orchestrator.models import (
    AgentMessage,
    AgentReflection,
    AgentRegistration,
    ReflectionVerdict,
)
from src.core.agent_orchestrator.registry import AgentRegistry

logger = structlog.get_logger()


class AgentOrchestrator:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._messages: list[AgentMessage] = []

    async def execute(
        self,
        task: str,
        context: dict | None = None,
        user_id: str | None = None,
        session: AsyncSession | None = None,
        preferred_agent: str | None = None,
    ) -> dict:
        task_id = str(uuid4())
        ctx = {**(context or {}), "user_id": user_id, "session": session}

        if preferred_agent:
            reg = self.registry.get(preferred_agent)
            if not reg:
                return {"task_id": task_id, "error": f"Agent '{preferred_agent}' not found"}
            return await self._dispatch(reg, task_id, task, ctx)

        matches = self.registry.find_by_task(task)
        if not matches:
            return {"task_id": task_id, "error": "No suitable agent found", "task": task}

        reg, _ = matches[0]
        return await self._dispatch(reg, task_id, task, ctx)

    def send_message(self, msg: AgentMessage) -> None:
        self._messages.append(msg)

    def get_messages(self, task_id: str | None = None) -> list[AgentMessage]:
        if task_id:
            return [m for m in self._messages if m.task_id == task_id]
        return list(self._messages)

    async def _dispatch(
        self,
        reg: AgentRegistration,
        task_id: str,
        task: str,
        context: dict,
    ) -> dict:
        start = time.monotonic()

        try:
            result = await self._call_agent(reg, task, context)
            duration = int((time.monotonic() - start) * 1000)
            confidence = result.get("confidence", result.get("score", 0.5))
            if isinstance(confidence, (int, float)):
                confidence = float(confidence)
            else:
                confidence = 0.5

            reflection = AgentReflection(
                agent_name=reg.name,
                task_id=task_id,
                objective=task,
                verdict=ReflectionVerdict.success,
                confidence=confidence,
                duration_ms=duration,
            )
            self._record_reflection(reflection)

            return {
                "task_id": task_id,
                "agent": reg.name,
                "result": result,
                "confidence": confidence,
                "duration_ms": duration,
            }
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            reflection = AgentReflection(
                agent_name=reg.name,
                task_id=task_id,
                objective=task,
                verdict=ReflectionVerdict.failure,
                confidence=0.0,
                duration_ms=duration,
                error=str(e),
            )
            self._record_reflection(reflection)
            logger.error("agent_dispatch_failed", agent=reg.name, task=task, error=str(e))
            return {
                "task_id": task_id,
                "agent": reg.name,
                "error": str(e),
                "duration_ms": duration,
            }

    async def _call_agent(self, reg: AgentRegistration, task: str, context: dict) -> dict:
        agent = reg.agent
        session = context.get("session")
        user_id = context.get("user_id")

        for cap in reg.capabilities:
            if cap.name == "tutoring":
                return await agent.answer(
                    question=task,
                    user_id=user_id,
                    grade_level=context.get("grade_level"),
                    topic=context.get("topic"),
                    language=context.get("language", "en"),
                    session=session,
                    use_rag=True,
                )
            if cap.name == "quiz_generation":
                return await agent.generate(
                    grade_level=context.get("grade_level", 10),
                    topic=context.get("topic", ""),
                    question_count=context.get("question_count", 5),
                    types=context.get("question_types"),
                    language=context.get("language", "en"),
                    session=session,
                )
            if cap.name == "lesson_planning":
                return await agent.generate(
                    grade_level=context.get("grade_level", 10),
                    topic=context.get("topic", ""),
                    duration_minutes=context.get("duration", 40),
                    language=context.get("language", "en"),
                    session=session,
                )
            if cap.name == "diagnostic_assessment":
                return await agent.generate(
                    grade_level=context.get("grade_level", 10),
                    topics=context.get("topics", [context.get("topic", "")]),
                    language=context.get("language", "en"),
                    session=session,
                )
            if cap.name == "translation":
                return await agent.translate(
                    text=context.get("text", task),
                    source_lang=context.get("source_lang", "en"),
                    target_lang=context.get("target_lang", "am"),
                    session=session,
                )
            if cap.name == "safety_review":
                return await agent.review(
                    content=context.get("content", task),
                    grade_level=context.get("grade_level"),
                    language=context.get("language", "en"),
                    session=session,
                )
            if cap.name == "diagram_generation":
                return await agent.generate(
                    prompt=task,
                    topic=context.get("topic", ""),
                    difficulty=context.get("difficulty", "beginner"),
                    session=session,
                    grade=context.get("grade_level", 10),
                )
            if cap.name == "student_progress":
                records = context.get("records", [])
                return await agent.analyze_progress(records, context.get("profile", {}))

        return {"error": f"No capability matched for task: {task}", "agent": reg.name}

    def _record_reflection(self, reflection: AgentReflection) -> None:
        logger.info(
            "agent_reflection",
            agent=reflection.agent_name,
            verdict=reflection.verdict.value,
            duration_ms=reflection.duration_ms,
        )

    def get_reflections(self, agent_name: str | None = None) -> list[AgentReflection]:
        return []
