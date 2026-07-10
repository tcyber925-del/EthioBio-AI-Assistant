import re

from src.agents.tutor.models import CitationEntry

CITATION_PATTERN = re.compile(r"\[id:([^\]]+)\]")


def extract_citations(
    response_text: str,
    evidence_items: list[dict],
) -> tuple[str, list[CitationEntry]]:
    evidence_map: dict[str, dict] = {}
    for item in evidence_items:
        eid = item.get("id", "")
        if eid:
            evidence_map[eid] = item

    matches = list(CITATION_PATTERN.finditer(response_text))
    if not matches:
        return response_text, []

    cleaned = CITATION_PATTERN.sub("", response_text).strip()
    cleaned = re.sub(r"  +", " ", cleaned)

    entries: list[CitationEntry] = []
    for m in matches:
        eid = m.group(1)
        evidence = evidence_map.get(eid, {})
        entries.append(
            CitationEntry(
                response_segment="",
                evidence_ids=[eid],
                source_names=[evidence.get("source_name", "unknown")] if evidence else ["unknown"],
            )
        )

    return cleaned, entries
