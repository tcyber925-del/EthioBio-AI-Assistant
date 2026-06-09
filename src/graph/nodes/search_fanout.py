"""Search Fanout Node for Agentic RAG.

Retrieves evidence from multiple indices in parallel using asyncio.gather.
Supports curriculum, evidence, and cross-session indices.
"""

import asyncio
import logging
from dataclasses import dataclass

from src.graph.state import AgentState
from src.retrieval.adapter import VectorStoreAdapter

logger = logging.getLogger(__name__)

MAX_RESULTS_PER_INDEX = 5
TOTAL_MAX_RESULTS = 15


@dataclass
class IndexResult:
    """Results from a single index search."""

    index_name: str
    query: str
    chunks: list[dict]
    score: float


async def search_single_index(
    adapter: VectorStoreAdapter, query: str, index_name: str, n_results: int = 5
) -> IndexResult:
    """Search a single index.

    Args:
        adapter: VectorStoreAdapter for retrieval.
        query: Search query.
        index_name: Index to search (curriculum, evidence, cross_session).
        n_results: Number of results to return.

    Returns:
        IndexResult with chunks and metadata.
    """
    try:
        results = adapter.search(query, n_results=n_results, collection_name=index_name)

        chunks = []
        for doc in results.get("documents", []):
            chunks.append(
                {
                    "content": doc.get("content", ""),
                    "metadata": doc.get("metadata", {}),
                    "score": doc.get("score", 0.0),
                    "source": index_name,
                }
            )

        avg_score = (
            sum(c.get("score", 0) for c in chunks) / len(chunks) if chunks else 0.0
        )

        return IndexResult(
            index_name=index_name,
            query=query,
            chunks=chunks,
            score=avg_score,
        )

    except Exception as e:
        logger.warning(f"Failed to search index {index_name}: {e}")
        return IndexResult(
            index_name=index_name, query=query, chunks=[], score=0.0
        )


def deduplicate_chunks(results: list[IndexResult]) -> list[dict]:
    """Deduplicate chunks across indices by content hash."""
    seen = set()
    deduplicated = []

    for result in results:
        for chunk in result.chunks:
            content = chunk.get("content", "")
            content_hash = hash(content[:100])

            if content_hash not in seen:
                seen.add(content_hash)
                deduplicated.append(chunk)

    return deduplicated


def rank_chunks(chunks: list[dict], max_results: int = TOTAL_MAX_RESULTS) -> list[dict]:
    """Rank chunks by score and return top results."""
    sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
    return sorted_chunks[:max_results]


class SearchFanoutNode:
    """Retrieves evidence from multiple indices.

    Phase 0: Sequential search across indices.
    Phase 1: Parallel search with asyncio.gather.
    """

    def __init__(self, adapter: VectorStoreAdapter):
        self.adapter = adapter

    async def _search_parallel(
        self, queries: list[str], indices: list[str]
    ) -> list[IndexResult]:
        """Execute parallel searches across all index-query combinations."""
        tasks = []

        for index_name in indices:
            for query in queries[:2]:  # Limit queries per index
                tasks.append(
                    search_single_index(self.adapter, query, index_name, MAX_RESULTS_PER_INDEX)
                )

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for r in results:
            if isinstance(r, IndexResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                logger.warning("search_task_failed", error=str(r))

        return valid_results

    async def __call__(self, state: AgentState) -> AgentState:
        """Execute multi-index retrieval in parallel.

        Args:
            state: AgentState with retrieval_queries and retrieval_indices.

        Returns:
            Updated AgentState with retrieved_chunks and coverage_score.
        """
        queries = state.retrieval_queries or [state.user_message]
        indices = state.retrieval_indices or ["curriculum"]

        # Execute parallel searches
        all_results = await self._search_parallel(queries, indices)

        # Deduplicate and rank
        deduplicated = deduplicate_chunks(all_results)
        ranked = rank_chunks(deduplicated)

        state.retrieved_chunks = ranked

        # Calculate coverage score
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

        # Calculate evidence strength
        state.evidence_strength = len(ranked) / TOTAL_MAX_RESULTS

        logger.info(
            "search_fanout_complete",
            indices_searched=len(indices),
            queries_used=len(queries),
            chunks_retrieved=len(ranked),
            coverage_score=state.coverage_score,
        )

        return state


def route_after_fanout(state: AgentState) -> str:
    """Route after search fanout based on results."""
    if state.coverage_score < 0.3:
        return "rewrite"

    return "sufficient_context"
