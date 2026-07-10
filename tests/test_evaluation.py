"""Tests for the evaluation module and gold set."""

import json
import os

import pytest


def test_gold_set_exists():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "evaluation", "gold_set.json")
    assert os.path.exists(path), "Gold set file not found"
    with open(path) as f:
        data = json.load(f)
    assert len(data) > 0, "Gold set is empty"
    for item in data:
        assert "id" in item
        assert "question" in item
        assert "expected_answer" in item
        assert "grade_level" in item


def test_ragas_module_imports():
    from src.evaluation.ragas_test import _heuristic_eval, evaluate_with_ragas, load_gold_set

    assert callable(evaluate_with_ragas)
    assert callable(load_gold_set)
    assert callable(_heuristic_eval)


@pytest.mark.asyncio
async def test_heuristic_evaluation():
    from src.evaluation.ragas_test import evaluate_with_ragas

    results = await evaluate_with_ragas(
        questions=["What is a cell?"],
        answers=["A cell is the basic unit of life."],
        contexts=[["The cell is the basic unit of life in all living organisms."]],
        ground_truths=["The cell is the basic unit of life."],
    )
    assert "faithfulness" in results
    assert "answer_relevancy" in results
    assert "method" in results
    assert results["method"] == "heuristic"


def test_gold_set_default():
    from src.evaluation.ragas_test import _default_gold_set

    items = _default_gold_set()
    assert len(items) >= 7, "Default gold set should have at least 7 items"
    types = {i["type"] for i in items}
    assert "tutor" in types
    assert "quiz" in types
    assert "lesson_plan" in types
