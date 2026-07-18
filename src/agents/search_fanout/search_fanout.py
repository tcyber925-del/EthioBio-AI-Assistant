"""Search Fanout Agent.

Rule-based agent that routes rewritten queries to the correct
retrievers and derives an execution strategy.

No LLM calls -- pure logic on query_groups.
"""

from src.agents.search_fanout.models import RetrievalStrategy, RetrievalTask
from src.agents.search_fanout.routing import derive_strategy, route_queries

MAX_QUERIES = 20


class SearchFanoutAgent:
    """Search Fanout Agent.

    Consumes query_groups from QueryRewriter, produces
    RetrievalTask list + RetrievalStrategy.

    The agent is stateless -- plan() is a pure function.
    """

    def __init__(self, max_queries: int = MAX_QUERIES):
        self.max_queries = max(max_queries, 0)

    def plan(
        self, query_groups: dict[str, list[str]]
    ) -> tuple[list[RetrievalTask], RetrievalStrategy]:
        """Create retrieval tasks and derive strategy from query groups.

        Caps total queries at max_queries, then delegates to
        route_queries() and derive_strategy().

        Args:
            query_groups: Dict mapping source_type to list of query strings.

        Returns:
            Tuple of (tasks, strategy).
        """
        capped_groups: dict[str, list[str]] = {}
        total = 0
        for source_type, queries in query_groups.items():
            remaining = self.max_queries - total
            if remaining <= 0:
                continue
            capped_groups[source_type] = queries[:remaining]
            total += len(capped_groups[source_type])

        tasks = route_queries(capped_groups)
        strategy = derive_strategy(capped_groups)

        return tasks, strategy
