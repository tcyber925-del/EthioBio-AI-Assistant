"""Pydantic models for the Tutor Synthesis Agent.

Defines TeachingStrategy enum, CitationEntry for grounded response
segments, and TutorResponse as the structured output of the agent.
"""

from enum import Enum

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


class TutorResponse(BaseModel):
    content: str
    confidence: float
    teaching_strategy: TeachingStrategy
    citation_map: list[CitationEntry]
    misconceptions_addressed: list[str]
    recommendations: list[str]
