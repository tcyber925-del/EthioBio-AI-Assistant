"""Search Fanout Node for Agentic RAG.

Retrieves evidence from multiple sources in parallel using asyncio.gather.
Uses SearchFanoutAgent for task planning and source routing.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.search_fanout.search_fanout import SearchFanoutAgent
from src.core.learning_intelligence.recommendation.services.service import (
    RecommendationService,
)
from src.graph.state import AgentState
from src.retrieval.adapter import VectorStoreAdapter

logger = logging.getLogger(__name__)

TOTAL_MAX_RESULTS = 15


class SearchFanoutNode:
    """LangGraph node that plans and executes parallel retrieval.

    Delegates task planning to SearchFanoutAgent, then executes
    via asyncio.gather across curriculum live retriever and
    stub retrievers for memory, learner, and recommendation.
    """

    def __init__(
        self,
        adapter: VectorStoreAdapter,
        max_queries: int = 20,
        db_session_factory: Optional[Callable[[], AsyncSession]] = None,
    ):
        self.adapter = adapter
        self.agent = SearchFanoutAgent(max_queries=max_queries)
        self.db_session_factory = db_session_factory

    async def _search_curriculum(self, query: str, n_results: int = 5) -> list[dict]:
        """Search curriculum index via VectorStoreAdapter."""
        try:
            results = self.adapter.search(
                query, n_results=n_results, collection_name="curriculum"
            )
            chunks = []
            for doc in results.get("documents", []):
                chunks.append(
                    {
                        "content": doc.get("content", ""),
                        "metadata": doc.get("metadata", {}),
                        "score": doc.get("score", 0.0),
                        "source": "curriculum",
                    }
                )
            return chunks
        except Exception as e:
            logger.warning("curriculum_search_failed: %s", str(e))
            return []

    async def _search_memory(self, query: str, user_id: Optional[str] = None) -> list[dict]:
        """Retrieve relevant conversation turns and educational summaries."""
        if not self.db_session_factory or not user_id:
            return []

        from datetime import datetime, timezone

        from src.database.models import ConversationTurn, MemoryEducationalSummary

        factory = self.db_session_factory()
        async with factory as session:
            terms = [t.lower() for t in query.split() if len(t) > 3]

            stmt = (
                select(ConversationTurn)
                .where(ConversationTurn.user_id == user_id)
                .order_by(desc(ConversationTurn.created_at))
                .limit(10)
            )
            result = await session.execute(stmt)
            turns = result.scalars().all()

            chunks = []
            now = datetime.now(timezone.utc)
            for turn in turns:
                content_lower = turn.content.lower()
                if terms and not any(t in content_lower for t in terms):
                    continue

                age_days = (now - turn.created_at).days if turn.created_at else 365
                if age_days == 0:
                    score = 1.0
                elif age_days < 7:
                    score = 0.8
                elif age_days < 30:
                    score = 0.5
                else:
                    score = 0.2

                chunks.append({
                    "content": turn.content,
                    "metadata": {
                        "id": str(turn.id),
                        "topic": turn.topic or "",
                        "role": turn.role,
                        "source_name": "conversation_turn",
                    },
                    "score": score,
                    "source": "memory",
                })

            if terms:
                summary_stmt = (
                    select(MemoryEducationalSummary)
                    .where(MemoryEducationalSummary.user_id == user_id)
                    .order_by(desc(MemoryEducationalSummary.created_at))
                    .limit(3)
                )
                summary_result = await session.execute(summary_stmt)
                summaries = summary_result.scalars().all()
                for summary in summaries:
                    content_lower = (summary.topic or "").lower()
                    if not any(t in content_lower for t in terms):
                        continue
                    chunks.append({
                        "content": summary.next_learning_goal or f"Summary for {summary.topic}",
                        "metadata": {
                            "id": str(summary.id),
                            "topic": summary.topic or "",
                            "source_name": "educational_summary",
                        },
                        "score": summary.confidence or 0.5,
                        "source": "memory",
                    })

            return chunks

    async def _search_learner(self, query: str, user_id: Optional[str] = None) -> list[dict]:
        """Retrieve learner profile data via SnapshotService."""
        if not self.db_session_factory or not user_id:
            return []

        from src.core.learning_intelligence.snapshot.snapshot_service import SnapshotService

        factory = self.db_session_factory()
        async with factory as session:
            snapshot_service = SnapshotService()
            snapshot = await snapshot_service.get_snapshot(session, user_id)

        if not snapshot:
            return []

        terms = [t.lower() for t in query.split() if len(t) > 3]
        chunks = []

        for topic, mastery in (snapshot.mastery_by_topic or {}).items():
            if terms and not any(t in topic.lower() for t in terms):
                continue
            severity_map = {"critical": 0.2, "moderate": 0.4, "mild": 0.6, "good": 0.8}
            severity = mastery.get("severity", "") if isinstance(mastery, dict) else ""
            score = severity_map.get(severity, 0.5)
            content = (
                f"Topic '{topic}': mastery={mastery.get('average_score', 0):.2f} "
                f"({severity}), attempts={mastery.get('attempt_count', 0)}"
            )
            chunks.append({
                "content": content,
                "metadata": {
                    "id": f"learner:mastery:{topic.lower().replace(' ', '_')}",
                    "topic": topic,
                    "source_name": "student_mastery",
                },
                "score": score,
                "source": "learner",
            })

        for topic, ability in (snapshot.ability_by_topic or {}).items():
            if terms and not any(t in topic.lower() for t in terms):
                continue
            chunks.append({
                "content": (
                    f"Topic '{topic}': ability={ability.get('ability_score', 0):.2f}, "
                    f"uncertainty={ability.get('uncertainty', 0):.2f}"
                ),
                "metadata": {
                    "id": f"learner:ability:{topic.lower().replace(' ', '_')}",
                    "topic": topic,
                    "source_name": "student_ability",
                },
                "score": min(1.0, ability.get("ability_score", 0) + 0.3),
                "source": "learner",
            })

        for mc in (snapshot.misconceptions or []):
            mc_topic = getattr(mc, "topic", "") or ""
            if terms and not any(t in mc_topic.lower() for t in terms):
                continue
            chunks.append({
                "content": (
                    f"Misconception in '{mc_topic}': "
                    f"{getattr(mc, 'pattern_type', '')} "
                    f"(frequency={getattr(mc, 'frequency', 0)})"
                ),
                "metadata": {
                    "id": f"learner:misconception:{mc_topic.lower().replace(' ', '_')}",
                    "topic": mc_topic,
                    "source_name": "misconception_pattern",
                },
                "score": min(0.7, getattr(mc, "frequency", 0) * 0.15),
                "source": "learner",
            })

        return chunks

    async def _search_recommendation(self, query: str, user_id: Optional[str] = None) -> list[dict]:
        """Retrieve recommendations via RecommendationService."""
        if not self.db_session_factory or not user_id:
            return []

        factory = self.db_session_factory()
        async with factory as session:
            service = RecommendationService()
            recommendations = await service.get_recommendations(session, user_id)

        if not recommendations:
            return []

        terms = [t.lower() for t in query.split() if len(t) > 3]
        chunks = []
        for rec in recommendations:
            topic_lower = (rec.topic or "").lower()
            if terms and not any(t in topic_lower for t in terms):
                if not any(t in rec.reason.lower() for t in terms):
                    continue
            chunks.append({
                "content": f"Recommendation for '{rec.topic}': {rec.reason}",
                "metadata": {
                    "id": rec.id or f"rec:{rec.action_type}:{(rec.topic or 'unknown').lower().replace(' ', '_')}",  # noqa: E501
                    "action_type": rec.action_type,
                    "topic": rec.topic or "",
                    "source_name": "recommendation_engine",
                },
                "score": rec.priority_score * 0.9,
                "source": "recommendation",
            })

        return chunks

    async def _safe_search(
        self, source: str, query: str, user_id: Optional[str] = None
    ) -> tuple[str, list[dict]]:
        """Execute a single source search, catching exceptions."""
        try:
            if source == "curriculum":
                result = await self._search_curriculum(query)
            elif source == "memory":
                result = await self._search_memory(query, user_id=user_id)
            elif source == "learner":
                result = await self._search_learner(query, user_id=user_id)
            elif source == "recommendation":
                result = await self._search_recommendation(query, user_id=user_id)
            else:
                logger.warning("unknown_source: %s", source)
                result = []
            return source, result
        except Exception as e:
            logger.warning("search_failed source=%s error=%s", source, str(e))
            return source, []

    async def __call__(self, state: AgentState) -> AgentState:
        query_groups = state.query_groups or {
            "curriculum": [state.user_message]
        }

        # Plan: create tasks and derive strategy
        tasks, strategy = self.agent.plan(query_groups)

        # Execute: gather unique (source, query) pairs in parallel
        user_id = str(state.user_id) if state.user_id else None
        seen = set()
        search_coros = []
        for task in tasks:
            key = (task.target_source, task.query)
            if key not in seen:
                seen.add(key)
                search_coros.append(
                    self._safe_search(task.target_source, task.query, user_id=user_id)
                )

        raw_results = await asyncio.gather(*search_coros, return_exceptions=True)

        # Merge results
        all_chunks: list[dict] = []
        source_results: dict[str, list[dict]] = {}
        for r in raw_results:
            if isinstance(r, Exception):
                logger.warning("search_task_exception: %s", str(r))
            elif isinstance(r, tuple):
                source, result = r
                if source not in source_results:
                    source_results[source] = []
                if isinstance(result, list):
                    source_results[source].extend(result)
                    all_chunks.extend(result)

        # Deduplicate by content
        seen_content = set()
        deduplicated = []
        for chunk in all_chunks:
            content = chunk.get("content", "")[:100]
            if content not in seen_content:
                seen_content.add(content)
                deduplicated.append(chunk)

        # Rank by score
        ranked = sorted(
            deduplicated, key=lambda x: x.get("score", 0), reverse=True
        )
        ranked = ranked[:TOTAL_MAX_RESULTS]

        state.retrieved_chunks = ranked
        state.retrieval_tasks = [t.model_dump() for t in tasks]
        state.retrieval_strategy = strategy.model_dump()
        state.retrieval_source_results = source_results

        # Coverage score
        if ranked:
            scores = [c.get("score", 0) for c in ranked]
            state.coverage_score = sum(scores) / len(scores)
        else:
            state.coverage_score = 0.0

        # Track evidence IDs
        evidence_ids = []
        for chunk in ranked:
            chunk_id = chunk.get("metadata", {}).get("id")
            if chunk_id:
                evidence_ids.append(chunk_id)
        state.evidence_ids = evidence_ids

        logger.info(
            "search_fanout_complete",
            sources_used=list(source_results.keys()),
            tasks_planned=len(tasks),
            chunks_retrieved=len(ranked),
            strategy=strategy.strategy_name,
        )

        return state


def route_after_fanout(state: AgentState) -> str:
    """Route after search fanout based on results."""
    if state.coverage_score < 0.3:
        return "rewrite"
    return "sufficient_context"
