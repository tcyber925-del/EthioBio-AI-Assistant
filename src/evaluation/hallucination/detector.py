import logging

from src.evaluation.hallucination.models import DetectionMode, HallucinationReport
from src.evaluation.hallucination.semantic import semantic_check
from src.evaluation.hallucination.structural import structural_check

logger = logging.getLogger(__name__)


class HallucinationDetector:
    def __init__(
        self,
        mode: DetectionMode = DetectionMode.FULL,
        router=None,
        overlap_threshold: float = 0.3,
    ):
        self.mode = mode
        self.router = router
        self.overlap_threshold = overlap_threshold

    async def analyze(
        self,
        response_text: str,
        citation_map: list[dict],
        evidence_items: list[dict],
    ) -> HallucinationReport:
        if not citation_map:
            return HallucinationReport(
                supported_claims=0,
                unsupported_claims=0,
                hallucination_rate=0.0,
                grounding_score=1.0,
                claim_assessments=[],
                detection_mode=self.mode,
            )

        if self.mode == DetectionMode.STRUCTURAL:
            return structural_check(citation_map, evidence_items)

        semantic = await semantic_check(
            citation_map,
            evidence_items,
            router=self.router if self.mode == DetectionMode.FULL else None,
            overlap_threshold=self.overlap_threshold,
        )

        return semantic
