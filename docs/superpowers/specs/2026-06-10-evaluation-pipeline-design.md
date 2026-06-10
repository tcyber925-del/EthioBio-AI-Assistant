# Evaluation Pipeline — Design Spec

**Date:** 2026-06-10
**Status:** Draft
**PRD:** PRD-009 — Agentic RAG Governance, Evaluation, and Observability (sub-project 2)

## Architecture

```
scenarios/*.yaml → BenchmarkRunner → per-scenario pipeline invocation
                        ↓
               MetricsCollector (reads PipelineMetrics + trace metadata)
                        ↓
               RegressionDetector (compares vs baselines/*.json)
                        ↓
               Report (JSON + exit code for CI)
```

The evaluation pipeline is a pytest-based benchmark suite. Scenarios are defined as YAML files, baselines are stored as JSON, and the runner produces a structured report.

## Components

### `src/evaluation/benchmark/scenarios/` — Scenario definitions

YAML files, one per scenario group. Format:

```yaml
name: "curriculum-grade-8"
description: "Grade 8 biology curriculum questions"
grade_level: 8
language: "en"
scenarios:
  - id: "cell-theory"
    question: "What is the cell theory and who proposed it?"
    expected_topics: ["cell theory"]
    tags: ["retrieval", "factual"]
  - id: "mitosis-vs-meiosis"
    question: "Compare and contrast mitosis and meiosis"
    expected_topics: ["cell division", "mitosis", "meiosis"]
    tags: ["comparison", "multi-step", "synthesis"]
```

Fields:
- `id` — unique scenario identifier
- `question` — user query sent to pipeline
- `expected_topics` — for coverage validation (optional)
- `tags` — for filtering (`factual`, `comparison`, `adversarial`, etc.)

### `src/evaluation/benchmark/runner.py` — BenchmarkRunner

Loads all scenario YAML files, invokes `run_graph()` for each, collects results.

```python
class BenchmarkRunner:
    def __init__(self, scenarios_dir: str, baselines_dir: str):
        self.scenarios_dir = scenarios_dir
        self.baselines_dir = baselines_dir

    async def run_all(
        self,
        filters: Optional[list[str]] = None,  # tag filters
        update_baselines: bool = False,
    ) -> BenchmarkReport:
        ...

    async def run_scenario(self, scenario: dict) -> ScenarioResult:
        # Invokes the same pipeline as the /chat endpoint
        # Uses scenario fields: question, grade_level, language, expected_topics
        state = await run_graph(
            user_message=scenario["question"],
            grade_level=scenario.get("grade_level", 8),
            language=scenario.get("language", "en"),
        )
        return ScenarioResult(
            scenario_id=scenario.id,
            passed=self._check_passed(scenario, state),
            metrics={
                "hallucination_rate": state.get("hallucination_rate", 0.0),
                "groundedness_score": state.get("groundedness_score", 0.0),
                "coverage_score": state.get("coverage_score", 0.0),
                "completion_time_ms": trace.duration_ms,
                "requires_teacher_review": state.get("requires_teacher_review", False),
            },
            error=state.get("error"),
            duration_ms=trace.duration_ms,
        )
```

### `src/evaluation/benchmark/models.py` — Data models

```python
@dataclass
class ScenarioResult:
    scenario_id: str
    passed: bool
    metrics: dict  # hallucination_rate, groundedness_score, coverage_score, etc.
    error: Optional[str]
    duration_ms: float

@dataclass
class BenchmarkReport:
    total_scenarios: int
    passed: int
    failed: int
    results: list[ScenarioResult]
    aggregate_metrics: dict
    regressions: list[str]
```

### `src/evaluation/benchmark/regression.py` — RegressionDetector

Compares actual metrics against stored baselines. Flags a regression when:

- `hallucination_rate` increased by >3 percentage points
- `groundedness_score` dropped by >5 percentage points
- `coverage_score` dropped by >5 percentage points
- `completion_rate` dropped below 95%
- Pipeline raised an unhandled error

```python
class RegressionDetector:
    def __init__(self, baselines: dict):
        self.baselines = baselines

    def check(self, actual: ScenarioResult) -> list[str]:
        ...
```

Baseline initialization: On first run (or when `--update-baselines` is set), the runner measures each scenario and writes the metric values as baselines with a 15% tolerance margin (e.g., measured hallucination_rate=0.08 → baseline max_hallucination_rate=0.092). Without baselines, all scenarios pass (regression detection is skipped).

Baseline JSON format (`baselines/curriculum-grade-8.json`):

```json
{
  "scenarios": {
    "cell-theory": {
      "min_groundedness": 0.80,
      "max_hallucination_rate": 0.10,
      "min_coverage_score": 0.70,
      "max_duration_ms": 10000
    }
  }
}
```

### `tests/benchmarks/` — pytest integration

Two marker groups:

- `pytest tests/benchmarks/ -m "smoke"` — quick (5-10) scenarios for rapid feedback
- `pytest tests/benchmarks/ -m "full"` — all scenarios (50+) for CI/nightly
- `pytest tests/benchmarks/ --update-baselines` — flag to update stored baselines

Test structure uses pytest fixtures for the BenchmarkRunner:

```python
@pytest.mark.smoke
@pytest.mark.asyncio
async def test_curriculum_scenarios(benchmark_runner):
    report = await benchmark_runner.run_all(filters=["curriculum"])
    assert report.passed == report.total_scenarios
```

### Report output

After each run, a JSON report is written to `benchmark_reports/<timestamp>.json` with:
- Per-scenario results (pass/fail, metrics, duration)
- Aggregate metrics
- Regression list (if any)
- Comparison to previous run

## Integration

No graph wiring changes needed. The evaluation pipeline is a standalone consumer of the existing `run_graph()` entry point. It uses the same `PipelineMonitor` infrastructure to collect metrics.

## Files

| Action | Path |
|--------|------|
| Create | `src/evaluation/benchmark/__init__.py` |
| Create | `src/evaluation/benchmark/models.py` |
| Create | `src/evaluation/benchmark/runner.py` |
| Create | `src/evaluation/benchmark/regression.py` |
| Create | `src/evaluation/benchmark/scenarios/curriculum-grade-8.yaml` |
| Create | `src/evaluation/benchmark/scenarios/adversarial.yaml` |
| Create | `tests/benchmarks/__init__.py` |
| Create | `tests/benchmarks/conftest.py` |
| Create | `tests/benchmarks/test_evaluation.py` |
| Create | `tests/benchmarks/baselines/` (empty dir or examples) |

## Test Plan

- Unit tests for `RegressionDetector` with known-good and known-bad metrics
- Unit tests for `BenchmarkRunner` with mocked `run_graph()`
- Integration test: load scenarios, run subset, verify report structure
- Regression test: supply baseline, verify detection of degraded metrics

## Future (out of scope for MVP)

- Web dashboard for benchmark history
- CI GitHub Action integration
- A/B experiment framework for comparing model versions
- Automated baseline drift alerts
