"""Tests for evaluation dataset JSON files — validates schema compliance."""

import json
from pathlib import Path

import pytest

from evaluation.datasets.schema import (
    ContextBenchmark,
    EvidenceBenchmark,
    FanoutBenchmark,
    LoopBenchmark,
    PlannerBenchmark,
    RewriterBenchmark,
    TutorBenchmark,
)

DATASETS_DIR = Path("evaluation/datasets")

SCHEMA_MAP = {
    "planner.json": PlannerBenchmark,
    "rewriter.json": RewriterBenchmark,
    "fanout.json": FanoutBenchmark,
    "evidence.json": EvidenceBenchmark,
    "context.json": ContextBenchmark,
    "loop.json": LoopBenchmark,
    "tutor.json": TutorBenchmark,
}


def _load_json(filename: str) -> list[dict]:
    path = DATASETS_DIR / filename
    assert path.exists(), f"Dataset {filename} not found"
    with open(path) as f:
        return json.load(f)


@pytest.mark.parametrize("filename,schema_cls", list(SCHEMA_MAP.items()))
def test_dataset_schema_compliance(filename, schema_cls):
    data = _load_json(filename)
    assert len(data) > 0, f"Dataset {filename} is empty"
    for entry in data:
        instance = schema_cls.model_validate(entry)
        assert instance.id, f"Entry missing id in {filename}"
        assert not instance.skip, f"Entry {instance.id} is marked skip, remove or set skip=false"


def test_all_datasets_present():
    """Ensure all 7 component datasets exist."""
    for filename in SCHEMA_MAP:
        assert (DATASETS_DIR / filename).exists(), f"Missing dataset: {filename}"


def test_planner_tasks_reasonable():
    """Planner expected_tasks make semantic sense."""
    data = _load_json("planner.json")
    for entry in data:
        assert len(entry["expected_tasks"]) >= 1
        assert all(isinstance(t, str) for t in entry["expected_tasks"])


def test_tutor_evidence_nonempty():
    """Tutor benchmarks have at least one evidence item."""
    data = _load_json("tutor.json")
    for entry in data:
        assert len(entry["input_evidence_items"]) >= 1
        for item in entry["input_evidence_items"]:
            assert "id" in item
            assert "content" in item


def test_evidence_dedup_counts():
    """Evidence dedup counts don't exceed input chunks."""
    data = _load_json("evidence.json")
    for entry in data:
        assert entry["expected_deduped_count"] <= len(entry["input_chunks"])


def test_context_boundaries():
    """Context benchmark scores are in valid range."""
    data = _load_json("context.json")
    for entry in data:
        assert 0.0 <= entry["input_coverage_score"] <= 1.0


def test_loop_iteration_counts():
    """Loop benchmarks don't exceed max iterations."""
    data = _load_json("loop.json")
    for entry in data:
        assert entry["input_iterations"] <= 5


def test_fanout_groups_nonempty():
    """Fanout benchmarks have at least one query group."""
    data = _load_json("fanout.json")
    for entry in data:
        assert len(entry["input_query_groups"]) >= 1


def test_rewriter_min_queries():
    """Rewriter expected_min_queries is positive."""
    data = _load_json("rewriter.json")
    for entry in data:
        assert entry["expected_min_queries"] >= 1
