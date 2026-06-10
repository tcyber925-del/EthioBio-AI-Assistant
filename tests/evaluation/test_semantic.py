from unittest.mock import AsyncMock, MagicMock

import pytest

from src.evaluation.hallucination.semantic import semantic_check


@pytest.mark.asyncio
async def test_heuristic_supported():
    citation_map = [
        {
            "response_segment": "Meiosis creates genetic diversity",
            "evidence_ids": ["bio_1"],
            "source_names": ["curriculum"],
        },
    ]
    evidence_items = [
        {
            "id": "bio_1",
            "content": "Meiosis is important for genetic diversity",
            "source_name": "curriculum",
            "confidence": 0.9,
        },
    ]
    report = await semantic_check(citation_map, evidence_items)
    assert report.supported_claims == 1
    assert report.unsupported_claims == 0


@pytest.mark.asyncio
async def test_heuristic_unsupported():
    citation_map = [
        {
            "response_segment": "Photosynthesis occurs in the Golgi apparatus",
            "evidence_ids": ["bio_1"],
            "source_names": ["curriculum"],
        },
    ]
    evidence_items = [
        {
            "id": "bio_1",
            "content": "The mitochondrion produces ATP through cellular respiration",
            "source_name": "curriculum",
            "confidence": 0.9,
        },
    ]
    report = await semantic_check(citation_map, evidence_items)
    assert report.unsupported_claims == 1


@pytest.mark.asyncio
async def test_empty_citation_map():
    report = await semantic_check([], [])
    assert report.supported_claims == 0
    assert report.unsupported_claims == 0
    assert report.hallucination_rate == 0.0


@pytest.mark.asyncio
async def test_llm_mode_with_router():
    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value={
        "content": "supported",
        "model": "test",
        "confidence": 0.95,
    })

    citation_map = [
        {
            "response_segment": "Meiosis creates diversity",
            "evidence_ids": ["bio_1"],
            "source_names": ["curriculum"],
        },
    ]
    evidence_items = [
        {
            "id": "bio_1",
            "content": "Meiosis diversity",
            "source_name": "curriculum",
            "confidence": 0.9,
        },
    ]
    report = await semantic_check(citation_map, evidence_items, router=mock_router)
    assert report.supported_claims == 1
