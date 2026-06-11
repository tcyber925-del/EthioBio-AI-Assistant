from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    PLANNER = "planner"
    QUERY_REWRITER = "rewriter"
    SEARCH_FANOUT = "fanout"
    EVIDENCE_GRAPH = "evidence_graph"
    SUFFICIENT_CONTEXT = "context"
    RETRIEVAL_LOOP = "loop"
    TUTOR = "tutor"


class EvaluationResult(BaseModel):
    component: ComponentType
    score: float = Field(ge=0.0, le=1.0)
    pass_status: bool
    latency_ms: float = 0.0
    failures: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)


class EvalSummary(BaseModel):
    total_components: int = 0
    passed: int = 0
    failed: int = 0
    aggregate_score: float = 0.0
    results: list[EvaluationResult] = Field(default_factory=list)
    regressions: list[str] = Field(default_factory=list)
    component_scores: dict[str, float] = Field(default_factory=dict)
