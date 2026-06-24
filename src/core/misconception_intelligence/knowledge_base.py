import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.misconception_intelligence.knowledge_base_data import (
    KNOWN_MISCONCEPTIONS,
    MISCONCEPTION_SEVERITIES,
)
from src.database.models import MisconceptionKnowledgeEntry

logger = structlog.get_logger()


class KnowledgeBaseService:
    async def ensure_seeded(self, session: AsyncSession) -> int:
        count = await session.scalar(select(func.count(MisconceptionKnowledgeEntry.id)))
        if count and count > 0:
            return count
        entries = [MisconceptionKnowledgeEntry(**data) for data in KNOWN_MISCONCEPTIONS]
        for e in entries:
            session.add(e)
        await session.flush()
        logger.info("knowledge_base_seeded", count=len(entries))
        return len(entries)

    async def classify(
        self, session: AsyncSession, topic: str, wrong_answer: str
    ) -> dict | None:
        text_lower = wrong_answer.lower()
        stmt = select(MisconceptionKnowledgeEntry).where(
            MisconceptionKnowledgeEntry.topic == topic
        )
        result = await session.execute(stmt)
        entries = result.scalars().all()

        best_match = None
        best_pattern_count = 0
        for entry in entries:
            matches = sum(
                1 for p in (entry.detection_patterns or [])
                if p.lower() in text_lower
            )
            if matches > best_pattern_count:
                best_pattern_count = matches
                best_match = entry

        if best_match and best_pattern_count > 0:
            return {
                "entry_id": str(best_match.id),
                "misconception": best_match.misconception,
                "explanation": best_match.explanation,
                "severity": best_match.severity,
                "recommended_strategies": best_match.recommended_strategies,
                "match_confidence": min(best_pattern_count * 0.5 + 0.3, 1.0),
            }
        return None

    async def list_by_topic(
        self, session: AsyncSession, topic: str | None = None
    ) -> list[MisconceptionKnowledgeEntry]:
        stmt = select(MisconceptionKnowledgeEntry)
        if topic:
            stmt = stmt.where(MisconceptionKnowledgeEntry.topic == topic)
        stmt = stmt.order_by(MisconceptionKnowledgeEntry.topic)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_topics(self, session: AsyncSession) -> list[str]:
        stmt = (
            select(MisconceptionKnowledgeEntry.topic)
            .distinct()
            .order_by(MisconceptionKnowledgeEntry.topic)
        )
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]

    def get_severity(self, severity_key: str) -> dict:
        default = MISCONCEPTION_SEVERITIES["misunderstanding"]
        return MISCONCEPTION_SEVERITIES.get(severity_key, default)

    def get_severities(self) -> dict:
        return MISCONCEPTION_SEVERITIES

    def compute_confidence(self, frequency: int, matched_kb: bool, severity_rank: int) -> float:
        base = 0.3 if matched_kb else 0.1
        freq_factor = min(frequency * 0.15, 0.4)
        severity_factor = (severity_rank - 1) * 0.1
        return round(min(base + freq_factor + severity_factor, 1.0), 2)

    def compute_severity(self, frequency: int, initial_severity: str | None = None) -> str:
        if initial_severity:
            return initial_severity
        if frequency >= 5:
            return "persistent_misconception"
        if frequency >= 3:
            return "misconception"
        if frequency >= 2:
            return "misunderstanding"
        return "knowledge_gap"
