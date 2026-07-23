"""Source routing and strategy derivation for Search Fanout.

Rule-based routing (no LLM). Maps QueryCategory source types
to retriever names via SOURCE_ROUTING dict lookup.
"""

import uuid

from src.agents.search_fanout.models import (
    RetrievalStrategy,
    RetrievalStrategyName,
    RetrievalTask,
)

DEFAULT_PRIORITY = 5

SOURCE_ROUTING: dict[str, str] = {
    "curriculum": "curriculum",
    "memory": "memory",
    "misconception": "memory",
    "learner_profile": "learner",
    "recommendation": "recommendation",
    "comparison": "curriculum",
    "definition": "curriculum",
}


def _resolve_source(source_type: str) -> str:
    """Resolve a query source_type to a retriever name."""
    return SOURCE_ROUTING.get(source_type, "curriculum")


def route_queries(
    query_groups: dict[str, list[str]],
    default_priority: int = DEFAULT_PRIORITY,
) -> list[RetrievalTask]:
    """Convert query_groups into a list of RetrievalTask objects.

    Each query in each group becomes a task routed to the
    appropriate retriever via SOURCE_ROUTING.

    Args:
        query_groups: Dict mapping source_type -> list of query strings.
        default_priority: Default priority for all tasks.

    Returns:
        List of RetrievalTask objects with unique IDs.
    """
    tasks: list[RetrievalTask] = []

    for source_type, queries in query_groups.items():
        target = _resolve_source(source_type)
        for query in queries:
            tasks.append(
                RetrievalTask(
                    id=uuid.uuid4().hex[:12],
                    query=query,
                    target_source=target,
                    priority=default_priority,
                    reasoning=f"Routed from {source_type} to {target}",
                )
            )

    return tasks


def derive_strategy(query_groups: dict[str, list[str]]) -> RetrievalStrategy:
    """Derive a RetrievalStrategy from the query_groups source types.

    Strategy is determined by which source types are present:

    | Sources Present | Strategy |
    |----------------|----------|
    | Only curriculum | SIMPLE |
    | curriculum + comparison | COMPARISON |
    | Includes memory | PERSONALIZED |
    | Includes recommendation | REMEDIATION |
    | 3+ sources | MULTI_HOP |

    Args:
        query_groups: Dict mapping source_type -> list of query strings.

    Returns:
        RetrievalStrategy with appropriate name and metadata.
    """
    source_types = set(query_groups.keys())
    expected = list(source_types)

    if len(source_types) >= 3:
        name = RetrievalStrategyName.MULTI_HOP
        mode = "multi"
        parallel = True
    elif "recommendation" in source_types:
        name = RetrievalStrategyName.REMEDIATION
        mode = "multi"
        parallel = True
    elif "memory" in source_types or "misconception" in source_types:
        name = RetrievalStrategyName.PERSONALIZED
        mode = "multi"
        parallel = True
    elif "comparison" in source_types:
        name = RetrievalStrategyName.COMPARISON
        mode = "multi"
        parallel = True
    else:
        name = RetrievalStrategyName.SIMPLE
        mode = "single"
        parallel = False

    return RetrievalStrategy(
        strategy_name=name,
        retrieval_mode=mode,
        parallel_execution=parallel,
        expected_sources=list({_resolve_source(s) for s in expected}),
    )
