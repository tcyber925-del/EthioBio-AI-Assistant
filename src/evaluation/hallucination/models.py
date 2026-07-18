from enum import Enum

from pydantic import BaseModel


class DetectionMode(str, Enum):
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    FULL = "full"


class ClaimAssessment(BaseModel):
    response_segment: str
    evidence_ids: list[str]
    supported: bool
    confidence: float
    reason: str = ""


class HallucinationReport(BaseModel):
    supported_claims: int
    unsupported_claims: int
    hallucination_rate: float
    grounding_score: float
    claim_assessments: list[ClaimAssessment]
    detection_mode: DetectionMode
