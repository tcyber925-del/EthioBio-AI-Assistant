from unittest.mock import AsyncMock, MagicMock

import pytest

from src.evaluation.hallucination.detector import HallucinationDetector
from src.evaluation.hallucination.models import DetectionMode


@pytest.mark.asyncio
async def test_detector_structural_only():
    detector = HallucinationDetector(mode=DetectionMode.STRUCTURAL)
    report = await detector.analyze(
        response_text="Meiosis creates diversity.",
        citation_map=[
            {
                "response_segment": "Meiosis creates diversity",
                "evidence_ids": ["bio_1"],
                "source_names": ["curriculum"],
            },
        ],
        evidence_items=[
            {
                "id": "bio_1",
                "content": "Meiosis diversity",
                "source_name": "curriculum",
                "confidence": 0.9,
            },
        ],
    )
    assert report.detection_mode == DetectionMode.STRUCTURAL
    assert report.supported_claims == 1


@pytest.mark.asyncio
async def test_detector_full_mode_heuristic():
    detector = HallucinationDetector(mode=DetectionMode.FULL)
    report = await detector.analyze(
        response_text="Meiosis creates genetic diversity.",
        citation_map=[
            {
                "response_segment": "Meiosis creates genetic diversity",
                "evidence_ids": ["bio_1"],
                "source_names": ["curriculum"],
            },
        ],
        evidence_items=[
            {
                "id": "bio_1",
                "content": "Meiosis is important for genetic diversity in cells",
                "source_name": "curriculum",
                "confidence": 0.9,
            },
        ],
    )
    assert report.supported_claims == 1
    assert report.hallucination_rate == 0.0


@pytest.mark.asyncio
async def test_detector_empty_inputs():
    detector = HallucinationDetector()
    report = await detector.analyze("", [], [])
    assert report.supported_claims == 0
    assert report.unsupported_claims == 0
    assert report.hallucination_rate == 0.0


@pytest.mark.asyncio
async def test_detector_full_mode_with_llm():
    mock_router = MagicMock()
    mock_router.route = AsyncMock(
        return_value={
            "content": "supported",
            "model": "test",
            "confidence": 0.95,
        }
    )

    detector = HallucinationDetector(mode=DetectionMode.FULL, router=mock_router)
    report = await detector.analyze(
        response_text="Meiosis creates diversity.",
        citation_map=[
            {
                "response_segment": "Meiosis creates diversity",
                "evidence_ids": ["bio_1"],
                "source_names": ["curriculum"],
            },
        ],
        evidence_items=[
            {
                "id": "bio_1",
                "content": "Meiosis diversity",
                "source_name": "curriculum",
                "confidence": 0.9,
            },
        ],
    )
    assert report.supported_claims == 1
    mock_router.route.assert_called_once()
