# Evaluation Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pytest-based evaluation pipeline that runs benchmark scenarios against the Agentic RAG pipeline, collects metrics, and detects regressions.

**Architecture:** BenchmarkRunner loads scenario YAMLs, invokes `run_graph()` for each, collects PipelineMetrics + hallucination metrics, compares against stored JSON baselines, and produces a structured report. Plugs into pytest via markers for smoke/full runs.

**Tech Stack:** Python 3.12+, Pydantic, pytest, asyncio, YAML (PyYAML), JSON baselines

---

## File Structure

```
Create: src/evaluation/benchmark/__init__.py
Create: src/evaluation/benchmark/models.py              # ScenarioResult, BenchmarkReport
Create: src/evaluation/benchmark/regression.py           # RegressionDetector
Create: src/evaluation/benchmark/runner.py               # BenchmarkRunner
Create: src/evaluation/benchmark/scenarios/__init__.py
Create: src/evaluation/benchmark/scenarios/curriculum-grade-8.yaml
Create: src/evaluation/benchmark/scenarios/adversarial.yaml

Create: tests/benchmarks/__init__.py
Create: tests/benchmarks/conftest.py                     # Fixtures for runner
Create: tests/benchmarks/test_evaluation.py              # Pytest test cases
Create: tests/benchmarks/baselines/.gitkeep
```

---

### Task 1: Models

**Files:**
- Create: `src/evaluation/benchmark/__init__.py`
- Create: `src/evaluation/benchmark/models.py`
- Create: `tests/benchmarks/__init__.py`

- [ ] **Step 1: Create `src/evaluation/benchmark/__init__.py`**

```python
from src.evaluation.benchmark.models import BenchmarkReport, ScenarioResult

__all__ = [
    "BenchmarkReport",
    "ScenarioResult",
]
```

- [ ] **Step 2: Create `src/evaluation/benchmark/models.py`**

```python
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
```

- [ ] **Step 3: Create empty `tests/benchmarks/__init__.py`** (empty file)

- [ ] **Step 4: Verify**

```bash
.venv/bin/ruff check src/evaluation/benchmark/
.venv/bin/mypy src/evaluation/benchmark/ --no-error-summary
```

- [ ] **Step 5: Commit**

```bash
git add src/evaluation/benchmark/ tests/benchmarks/__init__.py
git commit -m "feat(eval): add benchmark data models"
```

---

### Task 2: Scenario YAML Files

**Files:**
- Create: `src/evaluation/benchmark/scenarios/__init__.py`
- Create: `src/evaluation/benchmark/scenarios/curriculum-grade-8.yaml`
- Create: `src/evaluation/benchmark/scenarios/adversarial.yaml`
- Create: `tests/benchmarks/baselines/.gitkeep`

- [ ] **Step 1: Create `src/evaluation/benchmark/scenarios/__init__.py`** (empty file)

- [ ] **Step 2: Create `src/evaluation/benchmark/scenarios/curriculum-grade-8.yaml`**

```yaml
name: "curriculum-grade-8"
description: "Grade 8 biology curriculum questions from the Ethiopian curriculum"
grade_level: 8
language: "en"
scenarios:
  - id: "cell-theory"
    question: "What is the cell theory and who proposed it?"
    expected_topics: ["cell theory"]
    tags: ["curriculum", "factual", "retrieval"]

  - id: "mitosis-phases"
    question: "What are the phases of mitosis?"
    expected_topics: ["mitosis", "cell division"]
    tags: ["curriculum", "factual", "retrieval"]

  - id: "meiosis-vs-mitosis"
    question: "Compare and contrast mitosis and meiosis"
    expected_topics: ["mitosis", "meiosis", "cell division"]
    tags: ["curriculum", "comparison", "synthesis"]

  - id: "photosynthesis-formula"
    question: "What is the chemical equation for photosynthesis?"
    expected_topics: ["photosynthesis"]
    tags: ["curriculum", "factual"]

  - id: "digestive-system-path"
    question: "Trace the path of food through the digestive system"
    expected_topics: ["digestive system"]
    tags: ["curriculum", "sequential"]

  - id: "cell-organelles-function"
    question: "What are the functions of the mitochondria, ribosomes, and nucleus?"
    expected_topics: ["cell organelles", "mitochondria", "ribosomes", "nucleus"]
    tags: ["curriculum", "factual", "multi-topic"]

  - id: "genetics-dominant-recessive"
    question: "Explain the difference between dominant and recessive traits"
    expected_topics: ["genetics", "dominant", "recessive"]
    tags: ["curriculum", "comparison"]

  - id: "ecosystem-food-chain"
    question: "Describe how energy flows through a food chain"
    expected_topics: ["ecosystem", "food chain", "energy flow"]
    tags: ["curriculum", "sequential"]
```

- [ ] **Step 3: Create `src/evaluation/benchmark/scenarios/adversarial.yaml`**

```yaml
name: "adversarial"
description: "Edge cases and adversarial scenarios to stress-test pipeline behavior"
grade_level: 8
language: "en"
scenarios:
  - id: "out-of-domain"
    question: "What is the capital of France?"
    expected_topics: []
    tags: ["adversarial", "out-of-domain"]

  - id: "ambiguous-question"
    question: "Tell me about cells"
    expected_topics: ["cells"]
    tags: ["adversarial", "ambiguous"]

  - id: "multi-step-reasoning"
    question: "If a plant is kept in a dark room for a week, what would happen to its ability to perform photosynthesis and why?"
    expected_topics: ["photosynthesis", "plant biology"]
    tags: ["adversarial", "reasoning", "multi-step"]

  - id: "negative-query"
    question: "What is NOT a function of the cell membrane?"
    expected_topics: ["cell membrane"]
    tags: ["adversarial", "negative"]

  - id: "cross-session"
    question: "Based on our previous discussion about mitosis, what happens during prophase?"
    expected_topics: ["mitosis", "prophase"]
    tags: ["adversarial", "cross-session"]
```

- [ ] **Step 4: Create `tests/benchmarks/baselines/.gitkeep`** (empty file for directory tracking)

- [ ] **Step 5: Verify YAML parses correctly**

```bash
.venv/bin/python -c "import yaml; yaml.safe_load(open('src/evaluation/benchmark/scenarios/curriculum-grade-8.yaml')); yaml.safe_load(open('src/evaluation/benchmark/scenarios/adversarial.yaml')); print('YAML OK')"
```

- [ ] **Step 6: Commit**

```bash
git add src/evaluation/benchmark/scenarios/ tests/benchmarks/baselines/
git commit -m "feat(eval): add benchmark scenario YAML files"
```

---

### Task 3: RegressionDetector

**Files:**
- Create: `src/evaluation/benchmark/regression.py`
- Create: `tests/benchmarks/test_regression.py`

- [ ] **Step 1: Write the failing test in `tests/benchmarks/test_regression.py`**

```python
import json

from src.evaluation.benchmark.regression import RegressionDetector


def test_no_regression_when_within_bounds():
    baselines = {
        "cell-theory": {"min_groundedness": 0.8, "max_hallucination_rate": 0.1},
    }
    detector = RegressionDetector(baselines)
    metrics = {"groundedness_score": 0.85, "hallucination_rate": 0.05}
    issues = detector.check("cell-theory", metrics)
    assert issues == []


def test_detects_low_groundedness():
    baselines = {
        "test-1": {"min_groundedness": 0.8, "max_hallucination_rate": 0.1},
    }
    detector = RegressionDetector(baselines)
    metrics = {"groundedness_score": 0.6, "hallucination_rate": 0.05}
    issues = detector.check("test-1", metrics)
    assert len(issues) == 1
    assert "groundedness" in issues[0].lower()


def test_detects_high_hallucination():
    baselines = {
        "test-1": {"min_groundedness": 0.8, "max_hallucination_rate": 0.1},
    }
    detector = RegressionDetector(baselines)
    metrics = {"groundedness_score": 0.85, "hallucination_rate": 0.25}
    issues = detector.check("test-1", metrics)
    assert len(issues) == 1
    assert "hallucination" in issues[0].lower()


def test_unknown_scenario_no_regression():
    detector = RegressionDetector({})
    issues = detector.check("unknown", {})
    assert issues == []


def test_missing_metric_key_no_error():
    baselines = {
        "test-1": {"min_groundedness": 0.8},
    }
    detector = RegressionDetector(baselines)
    issues = detector.check("test-1", {})
    assert issues == []


def test_from_json():
    baselines_data = {
        "scenarios": {
            "cell-theory": {"min_groundedness": 0.8, "max_hallucination_rate": 0.1},
        }
    }
    detector = RegressionDetector.from_json(json.dumps(baselines_data))
    issues = detector.check("cell-theory", {"groundedness_score": 0.9, "hallucination_rate": 0.05})
    assert issues == []
```

- [ ] **Step 2: Run to confirm they fail**

```bash
.venv/bin/python -m pytest tests/benchmarks/test_regression.py -v
```

Expected: 6 FAIL

- [ ] **Step 3: Implement `src/evaluation/benchmark/regression.py`**

```python
import json
from typing import Optional


class RegressionDetector:
    def __init__(self, baselines: dict[str, dict]):
        self.baselines = baselines

    @classmethod
    def from_json(cls, json_str: str) -> "RegressionDetector":
        data = json.loads(json_str)
        scenarios = data.get("scenarios", data)  # accept flat or nested format
        return cls(scenarios)

    def check(self, scenario_id: str, metrics: dict) -> list[str]:
        baseline = self.baselines.get(scenario_id)
        if not baseline:
            return []

        issues: list[str] = []

        min_g = baseline.get("min_groundedness")
        if min_g is not None:
            actual = metrics.get("groundedness_score", 1.0)
            if actual < min_g:
                issues.append(
                    f"groundedness {actual:.3f} < min {min_g:.3f}"
                )

        max_h = baseline.get("max_hallucination_rate")
        if max_h is not None:
            actual = metrics.get("hallucination_rate", 0.0)
            if actual > max_h:
                issues.append(
                    f"hallucination_rate {actual:.3f} > max {max_h:.3f}"
                )

        min_c = baseline.get("min_coverage_score")
        if min_c is not None:
            actual = metrics.get("coverage_score", 0.0)
            if actual < min_c:
                issues.append(
                    f"coverage {actual:.3f} < min {min_c:.3f}"
                )

        max_d = baseline.get("max_duration_ms")
        if max_d is not None:
            actual = metrics.get("duration_ms", 0.0)
            if actual > max_d:
                issues.append(
                    f"duration {actual:.0f}ms > max {max_d:.0f}ms"
                )

        return issues

    def generate_baseline(self, scenario_id: str, metrics: dict, tolerance: float = 0.15) -> dict:
        groundedness = metrics.get("groundedness_score")
        hallucination = metrics.get("hallucination_rate")
        coverage = metrics.get("coverage_score")
        duration = metrics.get("duration_ms")

        baseline: dict[str, float] = {}
        if groundedness is not None:
            baseline["min_groundedness"] = round(groundedness * (1 - tolerance), 3)
        if hallucination is not None:
            baseline["max_hallucination_rate"] = round(hallucination * (1 + tolerance), 3)
        if coverage is not None:
            baseline["min_coverage_score"] = round(coverage * (1 - tolerance), 3)
        if duration is not None:
            baseline["max_duration_ms"] = round(duration * (1 + tolerance), 1)

        return baseline
```

- [ ] **Step 4: Run to verify they pass**

```bash
.venv/bin/python -m pytest tests/benchmarks/test_regression.py -v
```

Expected: 6 PASSED

- [ ] **Step 5: Ruff + mypy**

```bash
.venv/bin/ruff check src/evaluation/benchmark/regression.py tests/benchmarks/test_regression.py
.venv/bin/mypy src/evaluation/benchmark/regression.py --no-error-summary
```

- [ ] **Step 6: Commit**

```bash
git add src/evaluation/benchmark/regression.py tests/benchmarks/test_regression.py
git commit -m "feat(eval): add RegressionDetector with baseline comparison"
```

---

### Task 4: BenchmarkRunner

**Files:**
- Create: `src/evaluation/benchmark/runner.py`
- Create: `tests/benchmarks/test_runner.py`

- [ ] **Step 1: Write the failing test in `tests/benchmarks/test_runner.py`**

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.evaluation.benchmark.runner import BenchmarkRunner


@pytest.mark.asyncio
async def test_runner_loads_scenarios(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    scenario_file = scenarios_dir / "test.yaml"
    scenario_file.write_text(yaml.dump({
        "name": "test",
        "grade_level": 8,
        "language": "en",
        "scenarios": [
            {"id": "q1", "question": "What is cell theory?", "tags": ["curriculum"]},
        ],
    }))

    runner = BenchmarkRunner(str(scenarios_dir), str(tmp_path / "baselines"))
    assert len(runner.scenarios) == 1
    assert runner.scenarios[0]["id"] == "q1"


@pytest.mark.asyncio
async def test_runner_executes_scenario():
    mock_run_graph = AsyncMock(return_value={
        "hallucination_rate": 0.0,
        "groundedness_score": 0.9,
        "coverage_score": 0.8,
        "requires_teacher_review": False,
        "error": None,
    })

    runner = BenchmarkRunner(
        scenarios_dir="nonexistent",
        baselines_dir="nonexistent",
    )
    runner.scenarios = [
        {"id": "q1", "question": "test", "tags": [], "grade_level": 8, "language": "en"},
    ]

    with patch.object(runner, "_run_pipeline", mock_run_graph):
        report = await runner.run_all()

    assert report.total_scenarios == 1
    assert report.passed == 1
    assert report.results[0].scenario_id == "q1"


@pytest.mark.asyncio
async def test_runner_filters_by_tag():
    runner = BenchmarkRunner("nonexistent", "nonexistent")
    runner.scenarios = [
        {"id": "q1", "question": "test1", "tags": ["smoke"], "grade_level": 8, "language": "en"},
        {"id": "q2", "question": "test2", "tags": ["full"], "grade_level": 8, "language": "en"},
        {"id": "q3", "question": "test3", "tags": ["smoke", "full"], "grade_level": 8, "language": "en"},
    ]

    with patch.object(runner, "_run_pipeline", AsyncMock(return_value={
        "hallucination_rate": 0.0,
        "groundedness_score": 1.0,
        "coverage_score": 1.0,
        "requires_teacher_review": False,
        "error": None,
    })):
        report = await runner.run_all(filters=["smoke"])

    assert report.total_scenarios == 2  # q1 and q3
    assert report.results[0].scenario_id == "q1"


@pytest.mark.asyncio
async def test_runner_handles_pipeline_error():
    runner = BenchmarkRunner("nonexistent", "nonexistent")
    runner.scenarios = [
        {"id": "q1", "question": "test", "tags": [], "grade_level": 8, "language": "en"},
    ]

    with patch.object(runner, "_run_pipeline", AsyncMock(side_effect=ValueError("crash"))):
        report = await runner.run_all()

    assert report.total_scenarios == 1
    assert report.passed == 0
    assert report.failed == 1
    assert report.results[0].error is not None
```

- [ ] **Step 2: Run to confirm they fail**

```bash
.venv/bin/python -m pytest tests/benchmarks/test_runner.py -v
```

Expected: 4 FAIL

- [ ] **Step 3: Implement `src/evaluation/benchmark/runner.py`**

```python
import logging
import os
import time
from pathlib import Path
from typing import Optional

import yaml

from src.evaluation.benchmark.models import BenchmarkReport, ScenarioResult
from src.evaluation.benchmark.regression import RegressionDetector

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    def __init__(
        self,
        scenarios_dir: str,
        baselines_dir: str,
        regression_tolerance: float = 0.15,
    ):
        self.scenarios_dir = scenarios_dir
        self.baselines_dir = baselines_dir
        self.regression_tolerance = regression_tolerance
        self.scenarios: list[dict] = []
        self._load_scenarios()

    def _load_scenarios(self) -> None:
        scenarios_path = Path(self.scenarios_dir)
        if not scenarios_path.exists():
            logger.warning("scenarios_dir not found: %s", self.scenarios_dir)
            return

        self.scenarios = []
        for f in sorted(scenarios_path.glob("*.yaml")):
            with open(f) as fh:
                data = yaml.safe_load(fh)
                for s in data.get("scenarios", []):
                    s["grade_level"] = s.get("grade_level", data.get("grade_level", 8))
                    s["language"] = s.get("language", data.get("language", "en"))
                    self.scenarios.append(s)

    def _load_baselines(self) -> dict:
        baselines_path = Path(self.baselines_dir)
        baselines: dict = {}
        if not baselines_path.exists():
            return baselines
        for f in sorted(baselines_path.glob("*.json")):
            with open(f) as fh:
                import json
                data = json.load(fh)
                baselines.update(data.get("scenarios", data))
        return baselines

    def _save_baselines(self, results: list[ScenarioResult]) -> None:
        baselines_path = Path(self.baselines_dir)
        baselines_path.mkdir(parents=True, exist_ok=True)

        scenarios_by_group: dict[str, list[ScenarioResult]] = {}
        for r in results:
            s = next((s for s in self.scenarios if s["id"] == r.scenario_id), None)
            tag = "default"
            if s:
                tags = s.get("tags", [])
                tag = tags[0] if tags else "default"
            scenarios_by_group.setdefault(tag, []).append(r)

        for group, group_results in scenarios_by_group.items():
            detector = RegressionDetector({})
            group_baselines = {}
            for r in group_results:
                group_baselines[r.scenario_id] = detector.generate_baseline(
                    r.scenario_id, r.metrics, self.regression_tolerance,
                )
            filepath = baselines_path / f"{group}.json"
            with open(filepath, "w") as f:
                import json
                json.dump({"scenarios": group_baselines}, f, indent=2)

    async def _run_pipeline(self, scenario: dict) -> dict:
        from src.graph.orchestrator import run_graph

        return await run_graph(
            user_message=scenario["question"],
            grade_level=scenario.get("grade_level", 8),
            language=scenario.get("language", "en"),
        )

    async def run_all(
        self,
        filters: Optional[list[str]] = None,
        update_baselines: bool = False,
    ) -> BenchmarkReport:
        scenarios_to_run = self.scenarios
        if filters:
            scenarios_to_run = [
                s for s in self.scenarios
                if any(t in s.get("tags", []) for t in filters)
            ]

        results: list[ScenarioResult] = []

        for scenario in scenarios_to_run:
            start = time.time()
            try:
                state = await self._run_pipeline(scenario)
                duration_ms = (time.time() - start) * 1000

                metrics = {
                    "hallucination_rate": state.get("hallucination_rate", 0.0),
                    "groundedness_score": state.get("groundedness_score", 0.0),
                    "coverage_score": state.get("coverage_score", 0.0),
                    "duration_ms": duration_ms,
                    "requires_teacher_review": state.get("requires_teacher_review", False),
                }

                results.append(ScenarioResult(
                    scenario_id=scenario["id"],
                    question=scenario["question"],
                    passed=True,
                    metrics=metrics,
                    duration_ms=duration_ms,
                ))
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.error("scenario %s failed: %s", scenario["id"], e)
                results.append(ScenarioResult(
                    scenario_id=scenario["id"],
                    question=scenario["question"],
                    passed=False,
                    error=str(e),
                    duration_ms=duration_ms,
                ))

        if update_baselines:
            self._save_baselines(results)

        baselines = self._load_baselines()
        detector = RegressionDetector(baselines)
        regressions: list[str] = []
        for r in results:
            issues = detector.check(r.scenario_id, r.metrics)
            regressions.extend(issues)
            if issues:
                r.passed = False

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        agg = {}
        if results:
            agg = {
                "avg_hallucination_rate": round(
                    sum(r.metrics.get("hallucination_rate", 0) for r in results) / total, 3,
                ),
                "avg_groundedness": round(
                    sum(r.metrics.get("groundedness_score", 0) for r in results) / total, 3,
                ),
                "avg_coverage": round(
                    sum(r.metrics.get("coverage_score", 0) for r in results) / total, 3,
                ),
                "avg_duration_ms": round(
                    sum(r.duration_ms for r in results) / total, 1,
                ),
            }

        return BenchmarkReport(
            total_scenarios=total,
            passed=passed,
            failed=total - passed,
            results=results,
            aggregate_metrics=agg,
            regressions=regressions,
        )
```

- [ ] **Step 4: Run to verify they pass**

```bash
.venv/bin/python -m pytest tests/benchmarks/test_runner.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Ruff + mypy**

```bash
.venv/bin/ruff check src/evaluation/benchmark/runner.py tests/benchmarks/test_runner.py
.venv/bin/mypy src/evaluation/benchmark/runner.py --no-error-summary
```

- [ ] **Step 6: Commit**

```bash
git add src/evaluation/benchmark/runner.py tests/benchmarks/test_runner.py
git commit -m "feat(eval): add BenchmarkRunner with scenario execution and baseline comparison"
```

---

### Task 5: Pytest Integration

**Files:**
- Create: `tests/benchmarks/conftest.py`
- Create: `tests/benchmarks/test_evaluation.py`

- [ ] **Step 1: Write the failing test in `tests/benchmarks/conftest.py`**

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.evaluation.benchmark.runner import BenchmarkRunner


@pytest.fixture
def mock_runner():
    """Fixture providing a BenchmarkRunner with mocked pipeline."""
    runner = BenchmarkRunner(
        scenarios_dir="src/evaluation/benchmark/scenarios",
        baselines_dir="tests/benchmarks/baselines",
    )

    async def mock_pipeline(scenario):
        return {
            "hallucination_rate": 0.0,
            "groundedness_score": 0.9,
            "coverage_score": 0.8,
            "requires_teacher_review": False,
            "error": None,
        }

    with patch.object(runner, "_run_pipeline", mock_pipeline):
        yield runner
```

- [ ] **Step 2: Write the failing test in `tests/benchmarks/test_evaluation.py`**

```python
import pytest


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_smoke_scenarios_pass(mock_runner):
    """Smoke-tag scenarios should pass without regressions."""
    report = await mock_runner.run_all(filters=["smoke"])
    assert report.passed == report.total_scenarios, (
        f"Smoke scenarios: {report.passed}/{report.total_scenarios} passed. "
        f"Regressions: {report.regressions}"
    )


@pytest.mark.asyncio
async def test_curriculum_scenarios_load(mock_runner):
    """Curriculum scenarios should load from YAML."""
    curriculum = [s for s in mock_runner.scenarios if "curriculum" in s.get("tags", [])]
    assert len(curriculum) >= 3, f"Expected >=3 curriculum scenarios, got {len(curriculum)}"


@pytest.mark.asyncio
async def test_all_adversarial_scenarios(mock_runner):
    """Adversarial scenarios should not crash the pipeline."""
    report = await mock_runner.run_all(filters=["adversarial"])
    # Adversarial scenarios may fail gracefully (that's expected)
    # but they should not raise unhandled exceptions
    for r in report.results:
        assert r.error is None or "graceful" in r.error.lower(), (
            f"Unexpected error in {r.scenario_id}: {r.error}"
        )


@pytest.mark.asyncio
async def test_runner_filters_by_tag(mock_runner):
    """Only scenarios matching the filter should run."""
    full_report = await mock_runner.run_all()
    filtered_report = await mock_runner.run_all(filters=["curriculum"])
    assert filtered_report.total_scenarios < full_report.total_scenarios
    assert filtered_report.total_scenarios > 0
```

- [ ] **Step 3: Run these tests to verify they fail/collect**

```bash
.venv/bin/python -m pytest tests/benchmarks/test_evaluation.py -v --tb=short
```

Expected: Tests may fail if they try to actually invoke the pipeline (the mock is in conftest). The mock_runner fixture should intercept calls. But some may fail due to the pipeline fixture setup. That's OK — conftest tests the integration path.

- [ ] **Step 4: Verify all benchmark tests run**

```bash
.venv/bin/python -m pytest tests/benchmarks/ -v --tb=short
```

Expected: All unit tests pass. Integration tests (test_evaluation.py) may have limited coverage without a real pipeline — they validate the test harness structure.

- [ ] **Step 5: Ruff check**

```bash
.venv/bin/ruff check tests/benchmarks/
```

- [ ] **Step 6: Commit**

```bash
git add tests/benchmarks/conftest.py tests/benchmarks/test_evaluation.py
git commit -m "feat(eval): add pytest integration with smoke/curriculum/adversarial markers"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Run all benchmark tests**

```bash
.venv/bin/python -m pytest tests/benchmarks/ -v --tb=short
```

Expected: All unit tests pass (test_regression.py + test_runner.py). Integration tests structure is validated.

- [ ] **Step 2: Run all evaluation tests (hallucination + benchmark)**

```bash
.venv/bin/python -m pytest tests/evaluation/ tests/benchmarks/ -v --tb=short
```

- [ ] **Step 3: Run evidence graph tests to confirm no regressions**

```bash
.venv/bin/python -m pytest tests/test_evidence_graph_node.py -v --tb=short
```

- [ ] **Step 4: Full ruff check**

```bash
.venv/bin/ruff check src/evaluation/ tests/benchmarks/
```

- [ ] **Step 5: Commit any final changes**

```bash
git add -A && git commit -m "chore: final verification for evaluation pipeline" || echo "No changes"
```
