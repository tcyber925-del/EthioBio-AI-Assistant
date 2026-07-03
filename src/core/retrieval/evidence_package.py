from __future__ import annotations

from src.core.retrieval.citation import CitationFormatter
from src.core.retrieval.models import EvidencePackage, EvidenceSource


class EvidencePackageBuilder:
    def __init__(self, formatter: CitationFormatter | None = None):
        self._formatter = formatter or CitationFormatter()

    def build(
        self,
        query: str,
        results: list,
        degraded: bool = False,
    ) -> EvidencePackage:
        sources: list[EvidenceSource] = []
        for r in results:
            chunk_text = r.matches[0].text if r.matches else ""
            citation = self._formatter.build_citation(
                ko_id=r.ko_id,
                title=r.title,
                content=chunk_text,
                confidence=r.score,
            )
            source = EvidenceSource(
                ko_id=r.ko_id,
                title=r.title,
                content=chunk_text,
                chunk_index=r.matches[0].chunk_index if r.matches else 0,
                confidence=r.score,
                citation=citation,
            )
            sources.append(source)

        return EvidencePackage(
            query=query,
            sources=sources,
            total_results=len(results),
            degraded=degraded,
        )
