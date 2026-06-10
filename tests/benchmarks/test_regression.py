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
