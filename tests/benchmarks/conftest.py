from unittest.mock import patch

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
