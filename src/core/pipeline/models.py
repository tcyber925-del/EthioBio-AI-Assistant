from enum import StrEnum


class PipelineStage(StrEnum):
    VALIDATION = "validation"
    CONTENT_EXTRACTION = "content_extraction"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    PUBLICATION = "publication"
    ENRICHMENT = "enrichment"


class PipelineResult:
    def __init__(
        self,
        ko_id: str,
        success: bool,
        stage: str | None = None,
        error: str | None = None,
    ):
        self.ko_id = ko_id
        self.success = success
        self.stage = stage
        self.error = error
