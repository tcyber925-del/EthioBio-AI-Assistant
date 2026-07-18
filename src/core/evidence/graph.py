"""Evidence Graph service for Agentic RAG.

Central evidence registry. Immutable, self-contained records with provenance,
confidence, and dual query tracking.

Evidence is a first-class system artifact, not transient retrieval output.
Sessions define provenance boundaries; the repository defines persistence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import not_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import EvidenceRecord, EvidenceSession


@dataclass
class Evidence:
    """Single evidence unit in the Evidence Graph.

    Immutable once stored. Acts as both retrieval output and provenance artifact.
    """

    id: str
    source_type: str  # curriculum, memory, learner_profile, misconceptions
    source_name: str
    chunk_id: Optional[str]
    content: str  # full chunk text
    original_query: str
    retrieval_query: str
    retrieval_score: float
    rerank_score: float
    confidence: float
    retrieved_by: str  # which agent retrieved this
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    archived: bool = False
    expires_at: Optional[datetime] = None


@dataclass
class CoverageAnalysis:
    """Analysis of evidence coverage for a given session."""

    question_components: list[str]
    covered: list[bool]
    confidence: list[float]
    supporting_evidence: list[list[str]]


@dataclass
class EvidenceBundle:
    """Top evidence selected for generation."""

    evidence: list[Evidence]
    total_available: int
    selected_diversity: dict[str, int]  # source_type -> count


class EvidenceGraph:
    """Central evidence registry for Agentic RAG.

    PostgreSQL-backed persistent repository.
    Session-scoped retrieval for MVP (searches current session only).
    Stores full chunk content for immutability and auditability.

    Hierarchy: trace_id -> session_id -> evidence_id
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_session(
        self,
        session_id: str,
        trace_id: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """Create a new evidence session.

        Args:
            session_id: External session identifier (e.g., from AgentState).
            trace_id: PipelineMonitor trace ID for observability linkage.
            user_id: User UUID string.

        Returns:
            Internal session UUID.
        """
        record = EvidenceSession(
            id=uuid.uuid4(),
            session_id=session_id,
            trace_id=trace_id,
            user_id=uuid.UUID(user_id) if user_id else None,
            status="active",
        )
        self.session.add(record)
        await self.session.flush()
        return str(record.id)

    async def add(self, evidence: Evidence, internal_session_id: str) -> str:
        """Add an evidence record. Returns the evidence ID.

        Args:
            evidence: Evidence dataclass with content and provenance.
            internal_session_id: Internal session UUID from create_session().
        """
        record = EvidenceRecord(
            id=uuid.uuid4() if not evidence.id else uuid.UUID(evidence.id),
            session_id=uuid.UUID(internal_session_id),
            trace_id=evidence.trace_id,
            user_id=uuid.UUID(evidence.user_id) if evidence.user_id else None,
            source_type=evidence.source_type,
            source_name=evidence.source_name,
            chunk_id=evidence.chunk_id,
            content=evidence.content,
            original_query=evidence.original_query,
            retrieval_query=evidence.retrieval_query,
            retrieval_score=evidence.retrieval_score,
            rerank_score=evidence.rerank_score,
            confidence=evidence.confidence,
            retrieved_by=evidence.retrieved_by,
            archived=evidence.archived,
            expires_at=evidence.expires_at,
        )

        self.session.add(record)
        await self.session.flush()

        return str(record.id)

    async def get(self, evidence_id: str) -> Optional[Evidence]:
        """Retrieve evidence by ID."""
        result = await self.session.get(EvidenceRecord, uuid.UUID(evidence_id))

        if not result:
            return None

        return self._record_to_evidence(result)

    async def get_evidence_for_session(self, session_id: str) -> list[Evidence]:
        """Retrieve all evidence for a session (MVP retrieval scope).

        Args:
            session_id: External session identifier (not internal UUID).

        Returns:
            List of Evidence records for the session.
        """

        # Find internal sessions matching this external session_id
        session_stmt = select(EvidenceSession).where(EvidenceSession.session_id == session_id)
        session_result = await self.session.execute(session_stmt)
        internal_sessions = session_result.scalars().all()

        if not internal_sessions:
            return []

        internal_ids = [s.id for s in internal_sessions]

        stmt = (
            select(EvidenceRecord)
            .where(EvidenceRecord.session_id.in_(internal_ids))
            .where(not_(EvidenceRecord.archived))
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return [self._record_to_evidence(r) for r in records]

    async def get_evidence_for_trace(self, trace_id: str) -> list[Evidence]:
        """Retrieve all evidence for a trace (future conversation scope).

        Args:
            trace_id: PipelineMonitor trace ID.

        Returns:
            List of Evidence records across all sessions in this trace.
        """

        stmt = (
            select(EvidenceRecord)
            .where(EvidenceRecord.trace_id == trace_id)
            .where(not_(EvidenceRecord.archived))
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return [self._record_to_evidence(r) for r in records]

    async def get_evidence_for_user(self, user_id: str) -> list[Evidence]:
        """Retrieve all evidence for a user (future user-wide scope).

        Args:
            user_id: User UUID string.

        Returns:
            List of Evidence records for this user, ordered by recency.
        """

        stmt = (
            select(EvidenceRecord)
            .where(EvidenceRecord.user_id == uuid.UUID(user_id))
            .where(not_(EvidenceRecord.archived))
            .order_by(EvidenceRecord.created_at.desc())
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return [self._record_to_evidence(r) for r in records]

    async def get_coverage(self, session_id: str, question: str) -> CoverageAnalysis:
        """Analyze evidence coverage for a question."""
        evidence_list = await self.get_evidence_for_session(session_id)

        question_components = question.split()
        covered = [False] * len(question_components)
        confidence = [0.0] * len(question_components)
        supporting_evidence = [[] for _ in range(len(question_components))]

        for evidence in evidence_list:
            content_lower = evidence.content.lower()
            for i, component in enumerate(question_components):
                if component.lower() in content_lower:
                    covered[i] = True
                    confidence[i] = max(confidence[i], evidence.confidence)
                    supporting_evidence[i].append(evidence.id)

        return CoverageAnalysis(
            question_components=question_components,
            covered=covered,
            confidence=confidence,
            supporting_evidence=supporting_evidence,
        )

    async def find_missing(self, session_id: str) -> list[str]:
        """Detect missing information based on coverage analysis."""
        evidence_list = await self.get_evidence_for_session(session_id)

        if not evidence_list:
            return ["No evidence available"]

        missing = []
        for evidence in evidence_list:
            if evidence.confidence < 0.5:
                missing.append(f"Low confidence evidence: {evidence.source_name}")

        return missing

    async def archive_session(self, session_id: str) -> int:
        """Archive all evidence for a session (soft-delete).

        Evidence is immutable — never deleted. Archiving marks it as
        excluded from default retrieval scope.
        """

        stmt = (
            update(EvidenceRecord)
            .where(EvidenceRecord.session_id == uuid.UUID(session_id))
            .values(archived=True)
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def close_session(self, internal_session_id: str) -> None:
        """Mark a session as closed."""

        stmt = (
            update(EvidenceSession)
            .where(EvidenceSession.id == uuid.UUID(internal_session_id))
            .values(status="closed")
        )
        await self.session.execute(stmt)

    def _record_to_evidence(self, record: EvidenceRecord) -> Evidence:
        """Convert a DB record to an Evidence dataclass."""
        return Evidence(
            id=str(record.id),
            source_type=record.source_type,
            source_name=record.source_name,
            chunk_id=record.chunk_id,
            content=record.content,
            original_query=record.original_query,
            retrieval_query=record.retrieval_query,
            retrieval_score=record.retrieval_score,
            rerank_score=record.rerank_score,
            confidence=record.confidence,
            retrieved_by=record.retrieved_by,
            trace_id=record.trace_id,
            user_id=str(record.user_id) if record.user_id else None,
            archived=record.archived,
            expires_at=record.expires_at,
        )
