"""Evidence Confidence Scoring and Coverage Analysis.

Implements PRD-001B requirements for evidence scoring and coverage analysis.
"""

from dataclasses import dataclass, field


@dataclass
class ConfidenceScore:
    """Confidence score for evidence."""

    retrieval_score: float = 0.0
    rerank_score: float = 0.0
    source_quality: float = 0.0
    semantic_consistency: float = 0.0
    final_score: float = 0.0


@dataclass
class CoverageComponent:
    """Single coverage component."""

    topic: str
    covered: bool = False
    confidence: float = 0.0
    supporting_evidence: list[str] = field(default_factory=list)


@dataclass
class CoverageAnalysisResult:
    """Coverage analysis result."""

    components: list[CoverageComponent] = field(default_factory=list)
    coverage_score: float = 0.0
    missing_topics: list[str] = field(default_factory=list)
    covered_topics: list[str] = field(default_factory=list)


# Confidence weights per PRD-001B
CONFIDENCE_WEIGHTS = {
    "retrieval_score": 0.30,
    "rerank_score": 0.30,
    "source_quality": 0.20,
    "semantic_consistency": 0.20,
}

# Source quality scores
SOURCE_QUALITY = {
    "curriculum": 0.95,
    "evidence": 0.80,
    "cross_session": 0.70,
    "memory": 0.75,
    "learner_profile": 0.85,
    "misconceptions": 0.80,
}


def calculate_confidence(
    retrieval_score: float,
    rerank_score: float,
    source_type: str,
    semantic_consistency: float = 0.8,
) -> ConfidenceScore:
    """Calculate evidence confidence score.

    Args:
        retrieval_score: Score from retrieval (0.0-1.0).
        rerank_score: Score from reranker (0.0-1.0).
        source_type: Type of source (curriculum, memory, etc.).
        semantic_consistency: Semantic consistency score (0.0-1.0).

    Returns:
        ConfidenceScore with weighted final score.
    """
    source_quality = SOURCE_QUALITY.get(source_type, 0.5)

    final_score = (
        retrieval_score * CONFIDENCE_WEIGHTS["retrieval_score"]
        + rerank_score * CONFIDENCE_WEIGHTS["rerank_score"]
        + source_quality * CONFIDENCE_WEIGHTS["source_quality"]
        + semantic_consistency * CONFIDENCE_WEIGHTS["semantic_consistency"]
    )

    return ConfidenceScore(
        retrieval_score=retrieval_score,
        rerank_score=rerank_score,
        source_quality=source_quality,
        semantic_consistency=semantic_consistency,
        final_score=min(1.0, max(0.0, final_score)),
    )


def analyze_coverage(
    question: str, evidence_list: list[dict]
) -> CoverageAnalysisResult:
    """Analyze evidence coverage for a question.

    Args:
        question: Original user question.
        evidence_list: List of evidence dicts with 'content' field.

    Returns:
        CoverageAnalysisResult with coverage analysis.
    """
    question_words = [w.lower() for w in question.split() if len(w) > 3]

    components = []
    for word in question_words:
        covered = False
        confidence = 0.0
        supporting = []

        for evidence in evidence_list:
            content = evidence.get("content", "").lower()
            if word in content:
                covered = True
                confidence = max(confidence, evidence.get("score", 0.5))
                evidence_id = evidence.get("id", "")
                if evidence_id:
                    supporting.append(evidence_id)

        components.append(
            CoverageComponent(
                topic=word,
                covered=covered,
                confidence=confidence,
                supporting_evidence=supporting,
            )
        )

    covered_count = sum(1 for c in components if c.covered)
    total_count = len(components) if components else 1
    coverage_score = covered_count / total_count

    covered_topics = [c.topic for c in components if c.covered]
    missing_topics = [c.topic for c in components if not c.covered]

    return CoverageAnalysisResult(
        components=components,
        coverage_score=coverage_score,
        missing_topics=missing_topics,
        covered_topics=covered_topics,
    )


def detect_missing_information(
    coverage: CoverageAnalysisResult, threshold: float = 0.5
) -> list[str]:
    """Detect missing information based on coverage analysis.

    Args:
        coverage: CoverageAnalysisResult from analyze_coverage().
        threshold: Confidence threshold for considering a topic covered.

    Returns:
        List of missing topic areas.
    """
    missing = []

    for component in coverage.components:
        if not component.covered or component.confidence < threshold:
            missing.append(component.topic)

    return missing
