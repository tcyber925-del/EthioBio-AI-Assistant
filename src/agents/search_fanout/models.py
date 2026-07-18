"""Search Fanout data models.

Implements the PRD-004 schema:
- RetrievalTask: a single retrieval operation
- RetrievalStrategy: execution plan metadata
- RetrievalStrategyName: the 5 strategy variants
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class RetrievalStrategyName(str, Enum):
    """Strategies for retrieval execution."""

    SIMPLE = "SIMPLE"
    COMPARISON = "COMPARISON"
    PERSONALIZED = "PERSONALIZED"
    REMEDIATION = "REMEDIATION"
    MULTI_HOP = "MULTI_HOP"


class RetrievalTask(BaseModel):
    """A single retrieval operation targeting one source.

    Attributes:
        id: Unique task identifier.
        query: The query string to execute.
        target_source: Which retriever to use (curriculum, memory, etc.).
        priority: 1-10, higher is more important.
        estimated_cost: Reserved for future budget allocation.
        reasoning: Why this query routes to this source.
    """

    id: str = Field(description="Unique task identifier")
    query: str = Field(description="Query string to execute")
    target_source: str = Field(description="Target retriever name")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10")
    estimated_cost: float = Field(default=0.0, description="Estimated retrieval cost")
    reasoning: str = Field(default="", description="Why this query routes here")


class RetrievalStrategy(BaseModel):
    """Execution strategy metadata.

    Attributes:
        strategy_name: One of RetrievalStrategyName.
        retrieval_mode: "single" or "multi".
        parallel_execution: Whether sources run in parallel.
        expected_sources: Sources this strategy targets.
    """

    strategy_name: RetrievalStrategyName = Field(
        description="Strategy name from RetrievalStrategyName"
    )
    retrieval_mode: Literal["single", "multi"] = Field(
        default="single", description="'single' or 'multi'"
    )
    parallel_execution: bool = Field(default=False, description="Run sources in parallel")
    expected_sources: list[str] = Field(
        default_factory=list, description="Targeted retrieval sources"
    )
