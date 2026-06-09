"""Evidence Graph Node for Agentic RAG.

Normalizes raw retrieval output into persisted, selected, and scored
evidence records. Sits between PlanExecutor and SufficientContextNode.
"""
import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.evidence.graph import Evidence, EvidenceGraph
from src.core.evidence.scoring import (
    analyze_coverage,
    detect_missing_information,
)
from src.core.evidence.selector import EvidenceSelector
from src.core.evidence.summarizer import summarize_evidence
from src.graph.state import AgentState

logger = logging.getLogger(__name__)


class EvidenceGraphNode:
    """Wires Evidence Graph into the LangGraph pipeline.

    Creates an EvidenceSession, persists chunks as EvidenceRecords,
    selects the best evidence, analyzes coverage, and generates a summary.
    Falls back to passthrough when db_session_factory is None.
    """

    def __init__(
        self,
        db_session_factory: Optional[callable] = None,
        router=None,
    ):
        self.db_session_factory = db_session_factory
        self.graph: Optional[EvidenceGraph] = None
        self.selector = EvidenceSelector(graph=None, router=router)

    async def __call__(self, state: AgentState) -> AgentState:
        if not self.db_session_factory or not state.retrieval_source_results:
            logger.info("evidence_graph: passthrough (no db or no results)")
            return state

        session: AsyncSession = self.db_session_factory()
        self.graph = EvidenceGraph(session)

        trace_id = state.trace_id or ""
        session_key = state.session_id or trace_id or "default"
        user_id_str = str(state.user_id) if state.user_id else None

        # 1. Create session
        internal_session_id = await self.graph.create_session(
            session_id=session_key,
            trace_id=trace_id,
            user_id=user_id_str,
        )
        logger.info("evidence_graph: session_created %s", internal_session_id)

        # 2. Persist all chunks as evidence records
        evidence_count = 0
        for source_type, chunks in state.retrieval_source_results.items():
            for chunk in chunks:
                evidence = Evidence(
                    id="",
                    source_type=source_type,
                    source_name=chunk.get("source", source_type),
                    chunk_id=chunk.get("metadata", {}).get("id"),
                    content=chunk.get("content", ""),
                    original_query=state.user_message,
                    retrieval_query=state.user_message,
                    retrieval_score=chunk.get("score", 0.0),
                    rerank_score=chunk.get("score", 0.0),
                    confidence=chunk.get("score", 0.0),
                    retrieved_by="search_fanout",
                    trace_id=trace_id,
                    user_id=user_id_str,
                )
                await self.graph.add(evidence, internal_session_id)
                evidence_count += 1

        logger.info("evidence_graph: records_persisted %s", evidence_count)

        # 3. Get evidence for selection
        evidence_list = await self.graph.get_evidence_for_session(session_key)
        evidence_ids = [e.id for e in evidence_list]

        # 4. Select best evidence
        selected_ids = await self.selector.select_for_generation(
            evidence_ids=evidence_ids,
            question=state.user_message,
        )
        state.evidence_ids = selected_ids

        # 5. Analyze coverage
        evidence_dicts: list[dict[str, Any]] = [
            {
                "id": e.id,
                "content": e.content,
                "score": e.confidence,
                "source": e.source_type,
            }
            for e in evidence_list
        ]
        coverage = analyze_coverage(
            question=state.user_message,
            evidence_list=evidence_dicts,
        )
        state.coverage_score = coverage.coverage_score
        state.missing_information = detect_missing_information(coverage)

        # 6. Generate summary
        summary = summarize_evidence(
            evidence_list=evidence_dicts,
            question=state.user_message,
        )
        state.evidence_summary = summary.summary_text

        return state
