from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ComponentCategory(str, Enum):
    AGENT = "agent"
    DATA_COMPONENT = "data_component"
    PURE_FUNCTION = "pure_function"
    INTEGRATION = "integration"


class BenchmarkBase(BaseModel):
    id: str
    description: str = ""
    skip: bool = False


class PlannerBenchmark(BenchmarkBase):
    component_category: ComponentCategory = ComponentCategory.AGENT
    input_query: str
    expected_tasks: list[str]
    expected_complexity_low: bool = True
    expected_retrieval_domains: list[str] = Field(default_factory=list)


class RewriterBenchmark(BenchmarkBase):
    component_category: ComponentCategory = ComponentCategory.AGENT
    input_query: str
    input_subtasks: list[str] = Field(default_factory=list)
    expected_min_queries: int = 1
    expected_max_redundancy: float = 0.3
    expected_diverse_sources: bool = True


class FanoutBenchmark(BenchmarkBase):
    component_category: ComponentCategory = ComponentCategory.PURE_FUNCTION
    input_query_groups: dict[str, list[str]] = Field(default_factory=dict)
    expected_source_count: int = 1
    expected_correct_routes: list[str] = Field(default_factory=list)


class EvidenceBenchmark(BenchmarkBase):
    component_category: ComponentCategory = ComponentCategory.DATA_COMPONENT
    input_chunks: list[dict] = Field(default_factory=list)
    expected_deduped_count: int
    expected_coverage_min: float = 0.7
    expected_missing_topics: list[str] = Field(default_factory=list)


class ContextBenchmark(BenchmarkBase):
    component_category: ComponentCategory = ComponentCategory.PURE_FUNCTION
    input_evidence_count: int = 0
    input_coverage_score: float = 0.0
    input_previous_evidence_count: int = 0
    expected_sufficient: bool
    expected_continue: bool = False


class LoopBenchmark(BenchmarkBase):
    component_category: ComponentCategory = ComponentCategory.INTEGRATION
    input_iterations: int = 0
    input_coverage_gain: float = 0.0
    input_evidence_count: int = 0
    input_previous_evidence_count: int = 0
    expected_should_continue: bool
    expected_stop_reason: str = ""


class TutorBenchmark(BenchmarkBase):
    component_category: ComponentCategory = ComponentCategory.AGENT
    input_query: str
    input_evidence_items: list[dict] = Field(default_factory=list)
    input_grade_level: int = 8
    input_language: str = "en"
    expected_citations: list[str] = Field(default_factory=list)
    expected_grounding_min: float = 0.8
    expected_no_hallucination: bool = True


class BenchmarkCase(BaseModel):
    id: str
    category: str
    subject: str = ""
    question: str
    expected_topics: list[str] = Field(default_factory=list)
    required_agents: list[str] = Field(default_factory=list)
    expected_answer_traits: list[str] = Field(default_factory=list)
    expected_learning_outcome: str = ""
    grade_level: int = 8
    difficulty: str = "medium"
