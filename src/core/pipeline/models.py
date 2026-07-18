from dataclasses import dataclass
from enum import StrEnum


class PipelineStage(StrEnum):
    VALIDATION = "validation"
    CONTENT_EXTRACTION = "content_extraction"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    PUBLICATION = "publication"
    ENRICHMENT = "enrichment"


@dataclass
class PipelineResult:
    ko_id: str
    success: bool
    stage: str | None = None
    error: str | None = None
