from src.evaluation.hallucination.structural import structural_check


def test_all_claims_supported():
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
    report = structural_check(citation_map, evidence_items)
    assert report.supported_claims == 1
    assert report.unsupported_claims == 0
    assert report.hallucination_rate == 0.0
    assert report.grounding_score == 1.0


def test_missing_evidence_id():
    citation_map = [
        {
            "response_segment": "Claim",
            "evidence_ids": ["missing_id"],
            "source_names": ["curriculum"],
        },
    ]
    evidence_items = [
        {
            "id": "bio_1",
            "content": "Real",
            "source_name": "curriculum",
            "confidence": 0.9,
        },
    ]
    report = structural_check(citation_map, evidence_items)
    assert report.supported_claims == 0
    assert report.unsupported_claims == 1
    assert report.hallucination_rate == 1.0


def test_empty_citation_map():
    report = structural_check([], [])
    assert report.supported_claims == 0
    assert report.unsupported_claims == 0
    assert report.hallucination_rate == 0.0


def test_mixed_support():
    citation_map = [
        {
            "response_segment": "Good",
            "evidence_ids": ["bio_1"],
            "source_names": ["curriculum"],
        },
        {
            "response_segment": "Bad",
            "evidence_ids": ["missing"],
            "source_names": ["curriculum"],
        },
    ]
    evidence_items = [
        {
            "id": "bio_1",
            "content": "Real",
            "source_name": "curriculum",
            "confidence": 0.9,
        },
    ]
    report = structural_check(citation_map, evidence_items)
    assert report.supported_claims == 1
    assert report.unsupported_claims == 1
    assert report.hallucination_rate == 0.5
