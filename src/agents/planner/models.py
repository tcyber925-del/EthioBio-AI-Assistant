"""Plan and SubTask models for the Planner Agent.

Phase 0: Models defined. Implementation follows in subsequent stories.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ReasoningType(str, Enum):
    """Types of reasoning the Planner may identify."""

    FACT_LOOKUP = "fact_lookup"
    EXPLANATION = "explanation"
    COMPARISON = "comparison"
    MULTI_HOP = "multi_hop"
    PERSONALIZED = "personalized"
    SOCRATIC = "socratic"
    REMEDIATION = "remediation"


class ComplexityLevel(str, Enum):
    """Complexity levels for query classification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SubTask(BaseModel):
    """A single retrieval task within a Plan.

    Represents one unit of retrieval work to be executed
    by the PlanExecutor.
    """

    id: str = Field(description="Unique identifier for the subtask")
    type: str = Field(description="Type: curriculum, memory, learner_profile, misconceptions")
    objective: str = Field(description="What this subtask aims to retrieve")
    retrieval_sources: list[str] = Field(
        default_factory=list,
        description="Specific sources to query",
    )
    priority: int = Field(default=1, description="Execution order (1 = first)")
    expected_output: str = Field(default="", description="Description of expected evidence")


class Plan(BaseModel):
    """Structured execution plan for a user query.

    Created by the Planner Agent. Consumed by the PlanExecutor
    to drive sequential subtask execution.
    """

    objective: str = Field(description="High-level goal of the plan")
    complexity_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Query complexity (0.0-1.0)"
    )
    retrieval_domains: list[str] = Field(
        default_factory=list,
        description="Global retrieval scope",
    )
    subtasks: list[SubTask] = Field(
        default_factory=list, description="Ordered list of retrieval subtasks"
    )
    reasoning_type: ReasoningType = Field(
        default=ReasoningType.EXPLANATION,
        description="Primary reasoning type required",
    )
    estimated_iterations: int = Field(default=1, description="Expected retrieval iterations")
