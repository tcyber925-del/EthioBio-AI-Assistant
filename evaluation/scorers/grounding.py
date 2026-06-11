from __future__ import annotations

import re
from typing import Any


def score_topic_coverage(
    response_text: str,
    expected_topics: list[str],
) -> dict[str, Any]:
    """Score how well the response covers expected topics.

    Returns per-topic match status and aggregate coverage fraction.
    """
    if not expected_topics:
        return {"coverage": 1.0, "covered": [], "missed": [], "depth_avg": 1.0}

    response_lower = response_text.lower()
    covered: list[str] = []
    missed: list[str] = []
    depths: list[float] = []

    for topic in expected_topics:
        terms = topic.lower().split()
        matches = sum(1 for t in terms if t in response_lower)
        if matches > 0:
            covered.append(topic)
            depths.append(matches / len(terms))
        else:
            missed.append(topic)
            depths.append(0.0)

    coverage = len(covered) / len(expected_topics)
    depth_avg = sum(depths) / len(depths) if depths else 0.0

    return {
        "coverage": round(coverage, 3),
        "depth_avg": round(depth_avg, 3),
        "covered": covered,
        "missed": missed,
    }


def score_coherence(response_text: str) -> dict[str, Any]:
    """Score structural coherence of a response.

    Metrics:
      - paragraph_count and structure
      - transition word usage
      - sentence length consistency
    """
    if not response_text.strip():
        return {"coherence": 0.0, "paragraphs": 0, "transitions": 0, "consistency": 0.0}

    paragraphs = [p.strip() for p in response_text.split("\n\n") if p.strip()]
    para_count = len(paragraphs)

    transition_words = {
        "addition": ["additionally", "furthermore", "moreover", "also", "in addition"],
        "contrast": ["however", "on the other hand", "conversely", "nevertheless"],
        "cause": ["therefore", "as a result", "consequently", "thus", "because"],
        "sequence": ["first", "second", "third", "next", "then", "finally", "subsequently"],
        "example": ["for example", "for instance", "such as", "including"],
    }

    response_lower = response_text.lower()
    total_transitions = 0
    for group in transition_words.values():
        for word in group:
            if word in response_lower:
                total_transitions += 1

    sentences = _split_sentences(response_text)
    word_counts = [len(s.split()) for s in sentences if s.strip()]

    if len(word_counts) < 2:
        consistency = 1.0
    else:
        avg = sum(word_counts) / len(word_counts)
        variance = sum((wc - avg) ** 2 for wc in word_counts) / len(word_counts)
        std_dev = variance ** 0.5
        consistency = max(0.0, 1.0 - (std_dev / avg) * 0.5) if avg > 0 else 1.0

    has_structure = para_count >= 1
    transition_score = min(1.0, total_transitions / max(len(sentences), 1) * 3)

    coherence = (
        0.25 * (1.0 if has_structure else 0.0)
        + 0.35 * transition_score
        + 0.40 * consistency
    )

    return {
        "coherence": round(coherence, 3),
        "paragraphs": para_count,
        "sentences": len(sentences),
        "transitions": total_transitions,
        "consistency": round(consistency, 3),
    }


def score_factual_grounding(
    response_text: str,
    expected_topics: list[str],
) -> dict[str, Any]:
    """Combined factual grounding score using topic coverage and depth."""
    coverage = score_topic_coverage(response_text, expected_topics)
    coherence = score_coherence(response_text)

    factual = coverage["coverage"] * 0.6 + coverage["depth_avg"] * 0.4

    return {
        "factual_grounding": round(factual, 3),
        "topic_coverage": coverage["coverage"],
        "depth_avg": coverage["depth_avg"],
        "coherence": coherence["coherence"],
        "covered_topics": coverage["covered"],
        "missed_topics": coverage["missed"],
    }


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    text = text.replace("\n", " ")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]
