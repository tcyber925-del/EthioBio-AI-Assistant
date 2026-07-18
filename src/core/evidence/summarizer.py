"""Evidence Summarization for Agentic RAG.

Generates summaries of evidence for use by Tutor, Context Agent, and Evaluation.
"""

from dataclasses import dataclass, field


@dataclass
class EvidenceSummary:
    """Summary of evidence for generation."""

    supported_claims: list[str] = field(default_factory=list)
    unsupported_gaps: list[str] = field(default_factory=list)
    evidence_count: int = 0
    avg_confidence: float = 0.0
    source_distribution: dict[str, int] = field(default_factory=dict)
    summary_text: str = ""


def summarize_evidence(evidence_list: list[dict], question: str = "") -> EvidenceSummary:
    """Generate a summary of evidence.

    Args:
        evidence_list: List of evidence dicts with 'content', 'score', 'source' fields.
        question: Original question for context.

    Returns:
        EvidenceSummary with summary details.
    """
    if not evidence_list:
        return EvidenceSummary(
            summary_text="No evidence available.",
        )

    # Count evidence
    evidence_count = len(evidence_list)

    # Calculate average confidence
    scores = [e.get("score", 0.0) for e in evidence_list]
    avg_confidence = sum(scores) / len(scores) if scores else 0.0

    # Source distribution
    source_dist: dict[str, int] = {}
    for e in evidence_list:
        source = e.get("source", "unknown")
        source_dist[source] = source_dist.get(source, 0) + 1

    # Extract supported claims (simplified)
    supported = []
    for e in evidence_list[:5]:
        content = e.get("content", "")
        if content:
            # Take first sentence as claim
            first_sentence = content.split(".")[0]
            if first_sentence:
                supported.append(first_sentence.strip())

    # Generate summary text
    summary_parts = [f"{evidence_count} evidence items found."]
    if avg_confidence > 0.7:
        summary_parts.append("High confidence evidence.")
    elif avg_confidence > 0.4:
        summary_parts.append("Moderate confidence evidence.")
    else:
        summary_parts.append("Low confidence evidence.")

    if source_dist:
        sources = ", ".join(f"{k}: {v}" for k, v in source_dist.items())
        summary_parts.append(f"Sources: {sources}.")

    return EvidenceSummary(
        supported_claims=supported,
        unsupported_gaps=[],
        evidence_count=evidence_count,
        avg_confidence=avg_confidence,
        source_distribution=source_dist,
        summary_text=" ".join(summary_parts),
    )
