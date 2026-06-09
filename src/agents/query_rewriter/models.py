"""Query Rewriter data models.

Implements the PRD-003 schema:
- QueryBundle: groups rewritten queries with coverage estimate
- RewrittenQuery: single query with category, purpose, priority
- QueryCategory: the 7 allowed query categories
"""

from enum import Enum

from pydantic import BaseModel, Field


class QueryCategory(str, Enum):
    """Source-aware query categories for retrieval."""

    CURRICULUM = "curriculum"
    MEMORY = "memory"
    MISCONCEPTION = "misconception"
    LEARNER_PROFILE = "learner_profile"
    RECOMMENDATION = "recommendation"
    COMPARISON = "comparison"
    DEFINITION = "definition"


class RewrittenQuery(BaseModel):
    """A single rewritten query with source category and priority.

    Attributes:
        query: The rewritten, retrieval-oriented query string.
        source_type: One of the 7 QueryCategory values.
        purpose: Why this query was generated (e.g., "define meiosis").
        priority: Execution priority (1-10, higher = more important).
    """

    query: str = Field(description="The rewritten, retrieval-oriented query")
    source_type: str = Field(
        default="curriculum", description="Query category from QueryCategory enum"
    )
    purpose: str = Field(default="", description="Why this query was generated")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10")


class QueryBundle(BaseModel):
    """Collection of rewritten queries for a single user request.

    Attributes:
        original_query: The original user question or subtask objective.
        rewritten_queries: List of generated RewrittenQuery objects.
        estimated_coverage: Coverage score 0.0-1.0 estimating how well
            the queries cover the original request.
    """

    original_query: str = Field(description="Original user question or subtask objective")
    rewritten_queries: list[RewrittenQuery] = Field(
        default_factory=list,
        description="Generated retrieval-oriented queries",
    )
    estimated_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Estimated topic coverage score 0.0-1.0",
    )
