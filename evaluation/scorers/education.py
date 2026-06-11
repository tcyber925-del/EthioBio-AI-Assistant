from __future__ import annotations

import re
from typing import Any

EDUCATION_WEIGHTS: dict[str, float] = {
    "accuracy": 0.30,
    "clarity": 0.20,
    "relevance": 0.20,
    "completeness": 0.15,
    "personalization": 0.15,
}


def score_accuracy(
    response_text: str,
    expected_topics: list[str],
) -> float:
    """Fraction of expected topics present in response text.

    A topic counts as covered if its key terms appear in the response.
    """
    if not expected_topics:
        return 1.0
    response_lower = response_text.lower()
    covered = 0
    for topic in expected_topics:
        terms = topic.lower().split()
        if any(term in response_lower for term in terms):
            covered += 1
    return covered / len(expected_topics)


def score_clarity(response_text: str) -> float:
    """Heuristic clarity score based on sentence structure.

    Rewards:
      - Optimal sentence length (10-25 words)
      - Not too many very long or very short sentences
    """
    if not response_text.strip():
        return 0.0

    sentences = _split_sentences(response_text)
    if not sentences:
        return 0.0

    word_counts = [len(s.split()) for s in sentences if s.strip()]
    if not word_counts:
        return 0.0

    optimal = sum(1 for wc in word_counts if 10 <= wc <= 25)
    very_long = sum(1 for wc in word_counts if wc > 40)
    very_short = sum(1 for wc in word_counts if 1 <= wc < 5)

    clarity = optimal / len(word_counts)
    clarity -= very_long / len(word_counts) * 0.5
    clarity -= very_short / len(word_counts) * 0.3

    return max(0.0, clarity)


def score_relevance(
    response_text: str,
    expected_topics: list[str],
    question: str,
) -> float:
    """Response relevance via term overlap with expected topics and question."""
    response_lower = response_text.lower()
    query_terms = set(re.findall(r"[a-zA-Z]{3,}", question.lower()))

    topic_hits = 0
    for topic in expected_topics:
        terms = topic.lower().split()
        if any(term in response_lower for term in terms):
            topic_hits += 1

    topic_score = topic_hits / len(expected_topics) if expected_topics else 1.0

    query_hits = sum(1 for t in query_terms if t in response_lower)
    query_score = query_hits / len(query_terms) if query_terms else 1.0

    return 0.6 * topic_score + 0.4 * query_score


def score_completeness(
    response_text: str,
    expected_topics: list[str],
    expected_answer_traits: list[str],
) -> float:
    """Completeness based on coverage depth and structural markers."""
    if not expected_topics and not expected_answer_traits:
        return 1.0

    response_lower = response_text.lower()
    topic_depth = 0.0
    for topic in expected_topics:
        terms = topic.lower().split()
        matches = sum(1 for t in terms if t in response_lower)
        topic_depth += matches / len(terms) if terms else 1.0

    depth_score = topic_depth / len(expected_topics) if expected_topics else 1.0

    trait_markers: dict[str, list[str]] = {
        "comparison": ["similar", "different", "whereas", "unlike", "both"],
        "sequential": ["first", "then", "next", "finally", "step", "stage"],
        "reasoned": ["because", "therefore", "thus", "since", "leads to"],
        "step_by_step": ["first", "second", "third", "next", "then", "finally"],
    }

    expected_trait_set = set(expected_answer_traits)
    trait_present = 0
    trait_count = 0
    for trait, markers in trait_markers.items():
        if trait in expected_trait_set:
            trait_count += 1
            if any(m in response_lower for m in markers):
                trait_present += 1

    trait_score = trait_present / trait_count if trait_count else 1.0

    return 0.6 * depth_score + 0.4 * trait_score


def score_personalization(
    response_text: str,
    grade_level: int,
    expected_answer_traits: list[str],
) -> float:
    """Score for grade-appropriate language and personalization signals."""
    response_lower = response_text.lower()

    expected_set = set(expected_answer_traits)

    grade_score = _score_grade_appropriateness(response_text, grade_level)

    personalization_markers: list[str] = ["you", "your", "let's", "imagine", "think about"]
    personalization_hits = sum(1 for m in personalization_markers if m in response_lower)
    personalization_score = min(1.0, personalization_hits / 3.0)

    remedial_markers: list[str] = ["simply", "in other words", "that means", "think of it as"]
    remedial_hits = sum(1 for m in remedial_markers if m in response_lower)
    has_remedial_trait = "remedial" in expected_set or "patient" in expected_set
    remedial_score = min(1.0, remedial_hits / 2.0) if has_remedial_trait else 0.5

    return 0.4 * grade_score + 0.4 * personalization_score + 0.2 * remedial_score


def score_weighted_education(
    response_text: str,
    expected_topics: list[str],
    expected_answer_traits: list[str],
    question: str,
    grade_level: int,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run all education rubric dimensions and return weighted total."""
    w = weights or EDUCATION_WEIGHTS

    accuracy = score_accuracy(response_text, expected_topics)
    clarity = score_clarity(response_text)
    relevance = score_relevance(response_text, expected_topics, question)
    completeness = score_completeness(response_text, expected_topics, expected_answer_traits)
    personalization = score_personalization(response_text, grade_level, expected_answer_traits)

    total = (
        w["accuracy"] * accuracy
        + w["clarity"] * clarity
        + w["relevance"] * relevance
        + w["completeness"] * completeness
        + w["personalization"] * personalization
    )

    return {
        "accuracy": round(accuracy, 3),
        "clarity": round(clarity, 3),
        "relevance": round(relevance, 3),
        "completeness": round(completeness, 3),
        "personalization": round(personalization, 3),
        "weighted_score": round(total, 3),
        "weights": w,
    }


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    text = text.replace("\n", " ")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _score_grade_appropriateness(text: str, grade_level: int) -> float:
    """Simple grade-level readability proxy based on avg word length."""
    words = re.findall(r"[a-zA-Z]+", text)
    if not words:
        return 0.5

    avg_word_len = sum(len(w) for w in words) / len(words)

    if grade_level <= 7:
        return 1.0 if avg_word_len <= 5.5 else max(0.0, 1.0 - (avg_word_len - 5.5) * 0.3)
    elif grade_level <= 9:
        return 1.0 if 4.5 <= avg_word_len <= 6.5 else max(0.0, 1.0 - abs(avg_word_len - 5.5) * 0.2)
    elif grade_level <= 11:
        return 1.0 if 5.0 <= avg_word_len <= 7.5 else max(0.0, 1.0 - abs(avg_word_len - 6.0) * 0.15)
    else:
        return 1.0 if avg_word_len >= 5.5 else max(0.0, 1.0 - (5.5 - avg_word_len) * 0.2)
