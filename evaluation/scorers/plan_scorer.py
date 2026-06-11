from __future__ import annotations


def score_task_precision(predicted_tasks: list[str], expected_tasks: list[str]) -> float:
    """Fraction of predicted tasks that are in the expected set."""
    if not predicted_tasks:
        return 0.0
    expected_set = set(expected_tasks)
    matched = sum(1 for t in predicted_tasks if t in expected_set)
    return matched / len(predicted_tasks)


def score_task_recall(predicted_tasks: list[str], expected_tasks: list[str]) -> float:
    """Fraction of expected tasks that appear in predictions."""
    if not expected_tasks:
        return 1.0
    predicted_set = set(predicted_tasks)
    matched = sum(1 for t in expected_tasks if t in predicted_set)
    return matched / len(expected_tasks)


def score_task_f1(predicted_tasks: list[str], expected_tasks: list[str]) -> float:
    """F1 score for task list overlap."""
    precision = score_task_precision(predicted_tasks, expected_tasks)
    recall = score_task_recall(predicted_tasks, expected_tasks)
    if precision + recall == 0.0:
        return 0.0
    return 2.0 * (precision * recall) / (precision + recall)


def score_complexity_estimation(
    predicted_low: bool, expected_low: bool
) -> float:
    """1.0 if complexity classification matches, 0.0 otherwise."""
    return 1.0 if predicted_low == expected_low else 0.0
