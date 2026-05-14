"""Retrieval node — fetches curriculum context from vector store."""

from src.graph.state import AgentState
from src.retrieval.adapter import VectorStoreAdapter, RetrievalFilter


class RetrievalNode:
    def __init__(self, adapter: VectorStoreAdapter):
        self.adapter = adapter

    async def __call__(self, state: AgentState) -> AgentState:
        query = state.user_message
        if state.retrieval_query:
            query = state.retrieval_query

        filter_obj = RetrievalFilter(
            grade_level=state.grade_level,
            topic=state.topic,
        )

        results = await self.adapter.search(query, n_results=3, filter_obj=filter_obj)

        state.retrieved_chunks = [
            {"content": r.content, "metadata": r.metadata, "score": r.score, "source_id": r.source_id}
            for r in results
        ]
        state.context = self.adapter.format_context(results)

        return state


class SkipRetrievalNode:
    def __init__(self, adapter: VectorStoreAdapter = None):
        self.adapter = adapter

    async def __call__(self, state: AgentState) -> AgentState:
        state.retrieved_chunks = []
        state.context = ""
        return state
