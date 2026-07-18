from src.evaluation.hallucination.models import (
    ClaimAssessment,
    DetectionMode,
    HallucinationReport,
)


def structural_check(
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
            detection_mode=DetectionMode.STRUCTURAL,
        )

    valid_ids = {e["id"] for e in evidence_items if "id" in e}
    assessments: list[ClaimAssessment] = []

    for entry in citation_map:
        eids = entry.get("evidence_ids", [])
        missing = [eid for eid in eids if eid not in valid_ids]
        supported = len(missing) == 0
        assessments.append(
            ClaimAssessment(
                response_segment=entry.get("response_segment", ""),
                evidence_ids=eids,
                supported=supported,
                confidence=1.0 if supported else 0.0,
                reason="" if supported else f"evidence_id(s) not found: {missing}",
            )
        )

    total = len(assessments)
    supported_count = sum(1 for a in assessments if a.supported)
    unsupported_count = total - supported_count
    h_rate = unsupported_count / total if total > 0 else 0.0

    return HallucinationReport(
        supported_claims=supported_count,
        unsupported_claims=unsupported_count,
        hallucination_rate=h_rate,
        grounding_score=1.0 - h_rate,
        claim_assessments=assessments,
        detection_mode=DetectionMode.STRUCTURAL,
    )
