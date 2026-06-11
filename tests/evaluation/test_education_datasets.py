"""Tests for educational benchmark datasets (PRD-010C) — validates schema compliance."""

import json
from pathlib import Path

import pytest

from evaluation.datasets.schema import BenchmarkCase

DATASETS_DIR = Path("evaluation/datasets")

BENCHMARK_FILES = [
    "biology.json",
    "chemistry.json",
    "personalization.json",
    "misconceptions.json",
    "multihop.json",
]


def _load_json(filename: str) -> list[dict]:
    path = DATASETS_DIR / filename
    assert path.exists(), f"Benchmark dataset {filename} not found"
    with open(path) as f:
        return json.load(f)


@pytest.mark.parametrize("filename", BENCHMARK_FILES)
def test_benchmark_schema_compliance(filename):
    data = _load_json(filename)
    assert len(data) > 0, f"Dataset {filename} is empty"
    for entry in data:
        instance = BenchmarkCase.model_validate(entry)
        assert instance.id, f"Entry missing id in {filename}"
        assert instance.category, f"Entry {instance.id} missing category"
        assert instance.question, f"Entry {instance.id} missing question"


@pytest.mark.parametrize("filename", BENCHMARK_FILES)
def test_benchmark_has_expected_topics(filename):
    data = _load_json(filename)
    for entry in data:
        assert len(entry.get("expected_topics", [])) >= 1, (
            f"Entry {entry['id']} in {filename} has no expected_topics"
        )


@pytest.mark.parametrize("filename", BENCHMARK_FILES)
def test_benchmark_has_required_agents(filename):
    data = _load_json(filename)
    for entry in data:
        assert len(entry.get("required_agents", [])) >= 1, (
            f"Entry {entry['id']} in {filename} has no required_agents"
        )


@pytest.mark.parametrize("filename", BENCHMARK_FILES)
def test_benchmark_has_answer_traits(filename):
    data = _load_json(filename)
    for entry in data:
        assert len(entry.get("expected_answer_traits", [])) >= 1, (
            f"Entry {entry['id']} in {filename} has no expected_answer_traits"
        )


def test_all_benchmark_datasets_present():
    for filename in BENCHMARK_FILES:
        assert (DATASETS_DIR / filename).exists(), f"Missing benchmark: {filename}"


def test_biology_has_25_entries():
    data = _load_json("biology.json")
    assert len(data) == 25, f"Expected 25 biology entries, got {len(data)}"


def test_chemistry_has_10_entries():
    data = _load_json("chemistry.json")
    assert len(data) == 10, f"Expected 10 chemistry entries, got {len(data)}"


def test_personalization_has_10_entries():
    data = _load_json("personalization.json")
    assert len(data) == 10, f"Expected 10 personalization entries, got {len(data)}"


def test_misconceptions_has_8_entries():
    data = _load_json("misconceptions.json")
    assert len(data) == 8, f"Expected 8 misconception entries, got {len(data)}"


def test_multihop_has_8_entries():
    data = _load_json("multihop.json")
    assert len(data) == 8, f"Expected 8 multihop entries, got {len(data)}"


def test_grade_levels_in_range():
    for filename in BENCHMARK_FILES:
        data = _load_json(filename)
        for entry in data:
            assert 1 <= entry.get("grade_level", 0) <= 12, (
                f"Entry {entry['id']} in {filename} has invalid grade_level"
            )


def test_difficulty_values():
    for filename in BENCHMARK_FILES:
        data = _load_json(filename)
        valid = {"easy", "medium", "hard"}
        for entry in data:
            assert entry.get("difficulty") in valid, (
                f"Entry {entry['id']} in {filename} has invalid difficulty"
            )
