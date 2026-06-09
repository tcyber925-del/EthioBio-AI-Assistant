"""Query Rewriter Node for Agentic RAG.

Wires QueryRewriterAgent into the LangGraph pipeline.
Delegates query rewriting to the agent, populates AgentState
with rewritten queries and source-aware query groups.

PRD-003: Query Rewriter Agent.
"""

import logging

from src.agents.query_rewriter.models import QueryBundle, RewrittenQuery
from src.agents.query_rewriter.query_rewriter import QueryRewriterAgent
from src.graph.state import AgentState
from src.llm.router import ModelRouter

logger = logging.getLogger(__name__)


class QueryRewriterNode:
    """LangGraph node that rewrites queries via QueryRewriterAgent.

    Consumes state.execution_plan and state.subtasks to produce
    source-aware query groups for the SearchFanout node.
    """

    def __init__(self, router: ModelRouter | None = None):
        self.agent = QueryRewriterAgent(router) if router else None

    async def __call__(self, state: AgentState) -> AgentState:
        query = state.user_message
        subtasks = state.subtasks
        learner_snapshot = state.learner_snapshot or {}

        if self.agent:
            bundle = await self.agent.rewrite(
                user_query=query,
                subtasks=subtasks,
                learner_snapshot=learner_snapshot,
            )
        else:
            bundle = self._fallback_bundle(query, subtasks)

        flat_queries = [rq.query for rq in bundle.rewritten_queries]
        source_types = list({rq.source_type for rq in bundle.rewritten_queries})
        query_groups: dict[str, list[str]] = {}
        for rq in bundle.rewritten_queries:
            query_groups.setdefault(rq.source_type, []).append(rq.query)

        state.rewritten_queries = flat_queries
        state.query_intents = source_types
        state.query_groups = query_groups
        state.query_source_types = source_types
        state.coverage_estimate = bundle.estimated_coverage

        logger.info(
            "query_rewritten",
            original_query=query[:50],
            rewritten_count=len(flat_queries),
            source_types=source_types,
            coverage=bundle.estimated_coverage,
        )

        return state

    def _fallback_bundle(self, query: str, subtasks: list[dict]) -> QueryBundle:
        """Heuristic fallback when no LLM agent is available."""
        queries: list[RewrittenQuery] = []
        if subtasks:
            for i, st in enumerate(subtasks):
                objective = st.get("objective", st.get("description", ""))
                if not objective:
                    continue
                queries.append(
                    RewrittenQuery(
                        query=objective,
                        source_type=st.get("type", "curriculum"),
                        purpose=f"Subtask {i + 1}",
                        priority=max(1, 10 - i),
                    )
                )

        if not queries:
            queries.append(
                RewrittenQuery(
                    query=query,
                    source_type="curriculum",
                    purpose="Fallback: original query",
                    priority=5,
                )
            )

        return QueryBundle(
            original_query=query,
            rewritten_queries=queries,
            estimated_coverage=0.4,
        )


def route_after_rewrite(state: AgentState) -> str:
    """Route to SearchFanout after query rewriting."""
    return "search_fanout"
