"""Search Fanout Node for Agentic RAG.

Retrieves evidence from multiple sources in parallel using asyncio.gather.
Uses SearchFanoutAgent for task planning and source routing.
"""

import asyncio
import logging

from src.agents.search_fanout.search_fanout import SearchFanoutAgent
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

    def __init__(self, adapter: VectorStoreAdapter, max_queries: int = 20):
        self.adapter = adapter
        self.agent = SearchFanoutAgent(max_queries=max_queries)

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

    async def _search_memory(self, query: str) -> list[dict]:
        """Stub: Memory retriever.

        TODO: Implement real memory retriever (future PRD).
        """
        return []

    async def _search_learner(self, query: str) -> list[dict]:
        """Stub: Learner profile retriever.

        TODO: Implement real learner retriever (future PRD).
        """
        return []

    async def _search_recommendation(self, query: str) -> list[dict]:
        """Stub: Recommendation retriever.

        TODO: Implement real recommendation retriever (future PRD).
        """
        return []

    async def _safe_search(
        self, source: str, query: str
    ) -> tuple[str, list[dict]]:
        """Execute a single source search, catching exceptions."""
        try:
            if source == "curriculum":
                result = await self._search_curriculum(query)
            elif source == "memory":
                result = await self._search_memory(query)
            elif source == "learner":
                result = await self._search_learner(query)
            elif source == "recommendation":
                result = await self._search_recommendation(query)
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
        seen = set()
        search_coros = []
        for task in tasks:
            key = (task.target_source, task.query)
            if key not in seen:
                seen.add(key)
                search_coros.append(
                    self._safe_search(task.target_source, task.query)
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
