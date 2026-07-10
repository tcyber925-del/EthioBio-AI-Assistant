from __future__ import annotations

from src.core.retrieval.models import EvidenceSource, SourceCitation


class CitationFormatter:
    def format_badge(self, confidence: float) -> str:
        if confidence >= 0.9:
            return "high"
        if confidence >= 0.7:
            return "medium"
        return "low"

    def format_inline(self, source: EvidenceSource) -> str:
        badge = source.citation.confidence_badge
        return f"{source.title} [{badge} confidence]"

    def format_footnote(self, source: EvidenceSource, index: int) -> str:
        badge = source.citation.confidence_badge
        return f'[{index}] {source.title} -- "{source.citation.chunk_excerpt}" [{badge}]'

    def build_citation(
        self, ko_id: str, title: str, content: str, confidence: float
    ) -> SourceCitation:
        badge = self.format_badge(confidence)
        excerpt = content[:200]
        return SourceCitation(
            ko_id=ko_id,
            title=title,
            chunk_excerpt=excerpt,
            confidence_badge=badge,
        )
