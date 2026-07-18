from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemoryEvent, QuizAttempt, StudentMastery

logger = structlog.get_logger()


class EvidenceEngine:
    SOURCE_PRIORITY = {
        "quiz_attempt": 0.8,
        "mastery_record": 0.7,
        "memory_event": 0.6,
        "classroom_trend": 0.5,
    }

    async def gather_evidence(
        self,
        intent: str,
        user_id: UUID | None,
        session: AsyncSession,
    ) -> list[dict]:
        evidence = []

        if intent == "student_analysis" and user_id:
            evidence.extend(await self._get_mastery_evidence(user_id, session))
            evidence.extend(await self._get_quiz_evidence(user_id, session))
            evidence.extend(await self._get_memory_evidence(user_id, session))
        elif intent == "intervention_guidance" and user_id:
            evidence.extend(await self._get_mastery_evidence(user_id, session))
            evidence.extend(await self._get_memory_evidence(user_id, session))

        evidence.sort(key=lambda e: e.get("confidence", 0), reverse=True)
        return evidence[:10]

    async def _get_mastery_evidence(self, user_id: UUID, session: AsyncSession) -> list[dict]:
        result = await session.execute(
            select(StudentMastery).where(StudentMastery.user_id == user_id)
        )
        records = result.scalars().all()
        return [
            {
                "source": "mastery_record",
                "confidence": self.SOURCE_PRIORITY["mastery_record"],
                "content": {
                    "topic": r.topic,
                    "score": r.average_score,
                    "severity": r.severity,
                },
            }
            for r in records
        ]

    async def _get_quiz_evidence(self, user_id: UUID, session: AsyncSession) -> list[dict]:
        result = await session.execute(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user_id)
            .order_by(QuizAttempt.completed_at.desc())
            .limit(10)
        )
        records = result.scalars().all()
        return [
            {
                "source": "quiz_attempt",
                "confidence": self.SOURCE_PRIORITY["quiz_attempt"],
                "content": {
                    "quiz_id": str(r.quiz_id),
                    "score": r.score,
                    "total": r.total,
                    "percent": round(r.score / r.total * 100, 1) if r.total else 0,
                },
            }
            for r in records
        ]

    async def _get_memory_evidence(self, user_id: UUID, session: AsyncSession) -> list[dict]:
        result = await session.execute(
            select(MemoryEvent)
            .where(MemoryEvent.user_id == user_id)
            .order_by(MemoryEvent.created_at.desc())
            .limit(10)
        )
        records = result.scalars().all()
        return [
            {
                "source": "memory_event",
                "confidence": self.SOURCE_PRIORITY["memory_event"],
                "content": {
                    "event_type": r.event_type,
                    "metadata": r.event_metadata,
                    "created_at": str(r.created_at),
                },
            }
            for r in records
        ]

    @staticmethod
    def format_citations(evidence: list[dict]) -> str:
        if not evidence:
            return "No evidence available."
        lines = []
        for i, e in enumerate(evidence, 1):
            content = e.get("content", {})
            source = e.get("source", "unknown")
            confidence = e.get("confidence", 0)
            label = f"[{i}] ({source}, confidence: {confidence:.0%})"
            if source == "mastery_record":
                topic = content.get("topic", "?")
                score = content.get("score", "?")
                lines.append(f"{label} Topic '{topic}' mastery score: {score}")
            elif source == "quiz_attempt":
                s = content.get("score", "?")
                t = content.get("total", "?")
                p = content.get("percent", "?")
                lines.append(f"{label} Quiz score: {s}/{t} ({p}%)")
            elif source == "memory_event":
                meta = content.get("metadata", {})
                summary = meta if isinstance(meta, str) else str(meta)[:80]
                lines.append(f"{label} Event: {content.get('event_type')} - {summary}")
            else:
                lines.append(f"{label} {content}")
        return "\n".join(lines)
