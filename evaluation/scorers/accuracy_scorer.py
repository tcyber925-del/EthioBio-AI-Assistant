from __future__ import annotations


def score_binary_accuracy(
    predicted: bool,
    expected: bool,
) -> float:
    """Binary decision accuracy: 1.0 if match, 0.0 otherwise."""
    return 1.0 if predicted == expected else 0.0


def score_batch_accuracy(
    predictions: list[bool],
    expected: list[bool],
) -> float:
    """Proportion of correct binary decisions across a batch."""
    if not predictions or not expected:
        return 0.0
    correct = sum(1 for p, e in zip(predictions, expected) if p == e)
    return correct / max(len(predictions), len(expected))
