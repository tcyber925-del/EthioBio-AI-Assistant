from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScenarioResult:
    scenario_id: str
    question: str
    passed: bool
    metrics: dict = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class BenchmarkReport:
    total_scenarios: int = 0
    passed: int = 0
    failed: int = 0
    results: list[ScenarioResult] = field(default_factory=list)
    aggregate_metrics: dict = field(default_factory=dict)
    regressions: list[str] = field(default_factory=list)
