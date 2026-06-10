from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TeachingStrategy(str, Enum):
    SOCRATIC = "socratic"
    DIRECT_EXPLANATION = "direct_explanation"
    GUIDED_DISCOVERY = "guided_discovery"
    REMEDIATION = "remediation"
    ASSESSMENT_PREP = "assessment_prep"


class CitationEntry(BaseModel):
    response_segment: str
    evidence_ids: list[str]
    source_names: list[str]
    source_name: Optional[str] = None


class TutorResponse(BaseModel):
    content: str
    confidence: float
    teaching_strategy: TeachingStrategy
    citation_map: list[CitationEntry]
    misconceptions_addressed: list[str]
    recommendations: list[str]
