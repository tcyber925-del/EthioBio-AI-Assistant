from unittest.mock import AsyncMock, patch

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
        {
            "id": "q3", "question": "test3",
            "tags": ["smoke", "full"], "grade_level": 8, "language": "en",
        },
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
