from unittest.mock import AsyncMock, patch

import pytest

from src.evaluation.benchmark.runner import BenchmarkRunner
from tests.conftest import db_session as _db_session

db = _db_session


@pytest.fixture(autouse=True)
def _patch_embedder_and_vector_store(tmp_path):
    with (
        patch("src.rag.embedder.Embedder.embed_text", new=AsyncMock(return_value=[0.1] * 384)),
        patch("src.core.memory.vector_store.settings.vector_store_path", str(tmp_path)),
    ):
        yield


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
