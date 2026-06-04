import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.memory.retrieval_orchestrator import (
    MEMORY_TOKEN_BUDGET,
    RetrievalOrchestrator,
    estimate_tokens,
)

logger = structlog.get_logger()

SESSION_BUDGET = 200
SOCRATIC_BUDGET = 300
HISTORY_BUDGET = 500
SUMMARIES_BUDGET = 500


class ContextAssembler:
    def __init__(self):
        self.retrieval = RetrievalOrchestrator()

    async def assemble(
        self,
        user_id,
        topic: str | None,
        db: AsyncSession,
        session_state: dict | None = None,
        socratic_state: dict | None = None,
    ) -> str:
        sections = []
        remaining = MEMORY_TOKEN_BUDGET

        session_part = self._format_session(session_state)
        socratic_part = self._format_socratic(socratic_state)
        mastery_part = await self._format_mastery(user_id, topic, db)
        misconceptions_part = await self._format_misconceptions(user_id, topic, db)
        summaries_part = await self._format_summaries(user_id, topic)

        for label, part in [
            ("Current Session", session_part),
            ("Socratic State", socratic_part),
            ("Topic Mastery", mastery_part),
            ("Active Misconceptions", misconceptions_part),
            ("Recent Sessions", summaries_part),
        ]:
            if not part:
                continue
            tokens = estimate_tokens(part)
            if tokens > remaining:
                continue
            sections.append(f"### {label}\n{part}")
            remaining -= tokens

        if not sections:
            return ""

        result = "## Learner Context\n\n" + "\n\n".join(sections)
        logger.info(
            "context_assembled",
            total_tokens=MEMORY_TOKEN_BUDGET - remaining,
            sections=len(sections),
        )
        return result

    def _format_session(self, state: dict | None) -> str:
        if not state:
            return ""
        lines = [
            f"- Topic: {state.get('active_topic', 'unknown')}",
            f"- Mode: {state.get('tutoring_mode', 'direct')}",
        ]

        ctx = state.get("educational_context")
        if isinstance(ctx, dict):
            ctx_text = {k: v for k, v in ctx.items() if k not in ("messages", "recent_turns")}
            if ctx_text:
                lines.append(f"- Educational Context: {ctx_text}")

        questions = state.get("unresolved_questions")
        if questions and isinstance(questions, list) and len(questions) > 0:
            lines.append(f"- Unresolved Questions: {'; '.join(str(q) for q in questions[:3])}")
        return "\n".join(lines)

    def _format_socratic(self, state: dict | None) -> str:
        if not state or not state.get("socratic_stage"):
            return ""
        return (
            f"- Stage: {state.get('socratic_stage', '')}\n"
            f"- Focus: {state.get('current_focus', '')}\n"
            f"- Understanding: {state.get('student_understanding', '')}\n"
            f"- Gaps: {', '.join(str(g) for g in state.get('conceptual_gaps', [])[:3])}"
        )

    async def _format_mastery(self, user_id, topic: str | None, db: AsyncSession) -> str:
        try:
            from src.database.models import StudentMastery

            query = select(StudentMastery).where(StudentMastery.user_id == user_id)
            if topic:
                query = query.where(StudentMastery.topic == topic)
            query = query.order_by(StudentMastery.last_assessed_at.desc()).limit(5)

            result = await db.execute(query)
            records = result.scalars().all()
            if not records:
                return ""

            lines = []
            for r in records:
                label = f"{r.topic}: avg {r.average_score:.0%}"
                if r.severity != "good":
                    label += f" ({r.severity})"
                lines.append(f"- {label}")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("mastery_format_error", error=str(e))
            return ""

    async def _format_misconceptions(
        self, user_id, topic: str | None, db: AsyncSession,
    ) -> str:
        try:
            from src.database.models import MisconceptionPattern

            query = (
                select(MisconceptionPattern)
                .where(MisconceptionPattern.user_id == user_id)
                .where(MisconceptionPattern.resolved == False)  # noqa: E712
            )
            if topic:
                query = query.where(MisconceptionPattern.topic == topic)
            query = query.order_by(MisconceptionPattern.frequency.desc()).limit(3)

            result = await db.execute(query)
            patterns = result.scalars().all()
            if not patterns:
                return ""

            lines = []
            for p in patterns:
                desc = p.pattern_description[:120]
                lines.append(f"- {desc} (frequency: {p.frequency})")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("misconceptions_format_error", error=str(e))
            return ""

    async def _format_summaries(self, user_id, topic: str | None) -> str:
        try:
            if topic:
                results = await self.retrieval.search_by_topic(topic, user_id=str(user_id))
            else:
                results = await self.retrieval.search(
                    "educational history", n_results=3, user_id=str(user_id),
                )
            if not results:
                return ""

            lines = []
            for r in results:
                meta = r.metadata
                understanding = meta.get("understanding_level", "")
                confidence = meta.get("confidence", 0.0)
                lines.append(
                    f"- [{meta.get('topic', '?')}] Level: {understanding} "
                    f"(confidence: {confidence:.2f}) — {r.content[:150]}"
                )
            return "\n".join(lines)
        except Exception as e:
            logger.warning("summaries_format_error", error=str(e))
            return ""
