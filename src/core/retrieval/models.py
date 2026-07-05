from __future__ import annotations

from pydantic import BaseModel


class TextMatch(BaseModel):
    text: str
    chunk_index: int
    score: float


class SourceCitation(BaseModel):
    ko_id: str
    title: str
    chunk_excerpt: str
    confidence_badge: str


class EvidenceSource(BaseModel):
    ko_id: str
    title: str
    content: str
    chunk_index: int
    confidence: float
    citation: SourceCitation


class EvidencePackage(BaseModel):
    query: str
    sources: list[EvidenceSource]
    total_results: int
    degraded: bool = False


class RetrievalResult(BaseModel):
    ko_id: str
    title: str
    content_type: str
    score: float
    matches: list[TextMatch]
    workspace_id: str | None = None
    enrichment: dict | None = None


class RoutingPlan(BaseModel):
    layers: list[str]
    primary_source: str
    strategy: str
