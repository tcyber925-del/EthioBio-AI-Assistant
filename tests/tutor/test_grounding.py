from src.agents.tutor.grounding import extract_citations


def test_extracts_single_citation():
    text = "Meiosis produces diverse cells. [id:bio_ch4_22]"
    cleaned, entries = extract_citations(text, [
        {"id": "bio_ch4_22", "content": "Meiosis creates diversity", "source_name": "curriculum"}
    ])
    assert cleaned == "Meiosis produces diverse cells."
    assert len(entries) == 1
    assert entries[0].evidence_ids == ["bio_ch4_22"]
    assert "curriculum" in entries[0].source_names


def test_extracts_multiple_citations():
    text = "Mitosis has 4 phases. [id:bio_ch3_10] Meiosis has 8. [id:bio_ch4_22]"
    cleaned, entries = extract_citations(text, [
        {"id": "bio_ch3_10", "content": "Mitosis phases", "source_name": "curriculum"},
        {"id": "bio_ch4_22", "content": "Meiosis stages", "source_name": "curriculum"},
    ])
    assert len(entries) == 2


def test_no_citations_returns_empty():
    text = "Just some text without citations."
    cleaned, entries = extract_citations(text, [])
    assert cleaned == text
    assert entries == []


def test_unknown_evidence_id():
    text = "Some claim. [id:unknown_id]"
    cleaned, entries = extract_citations(text, [
        {"id": "known_id", "content": "Known", "source_name": "curriculum"}
    ])
    assert len(entries) == 1
    assert entries[0].evidence_ids == ["unknown_id"]
    assert entries[0].source_names == ["unknown"]
