"""Textbook-specific extraction helpers.

Ported from the legacy ingest scripts (`scripts/ingest_curriculum.py`) so the
production pipeline can recover printed page numbers and unit/heading metadata
that were lost when ingestion moved to `src/core/pipeline/service.py`.
"""

import re

# Number of front-matter pages (cover, TOC, preface) before content, per grade.
# Used only as a fallback when no page number can be extracted from the page
# text itself (printed number in footer/header).
FRONT_MATTER_PAGES = {9: 7, 10: 3, 11: 10, 12: 5}


def extract_pdf_pages(path: str) -> list[dict]:
    """Extract per-page text from a PDF, 1-based page indices.

    Returns a list of ``{"text": str, "pdf_page": int}`` dicts, skipping pages
    that yield no text. ``pdf_page`` is the raw PDF page index (1-based), not
    the printed textbook page number.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text and text.strip():
            pages.append({"text": text.strip(), "pdf_page": i})
    return pages


def extract_page_number(page_text: str, pdf_page_num: int, grade: int) -> int:
    """Extract the printed textbook page number from the page footer or header.

    Ethiopian textbooks print the page number either in the footer (grades
    9/10/11) or in the page header (grade 12). Falls back to the PDF index
    minus the grade's front-matter page count. Unknown grades fall back to the
    raw PDF index.
    """
    if grade not in FRONT_MATTER_PAGES:
        return max(1, pdf_page_num)
    lines = page_text.strip().split("\n")
    if not lines:
        return max(1, pdf_page_num - FRONT_MATTER_PAGES.get(grade, 3))

    # Pattern 1: standalone number in the last few lines (footer) — most reliable
    for line in reversed(lines[-3:]):
        line = line.strip()
        if re.match(r"^\d{1,3}$", line):
            n = int(line)
            if 1 <= n <= 600:
                return n

    footer_region = "\n".join(lines[-3:]).strip()

    # Pattern 2: "Grade X Biology N" (number after grade/subject)
    m = re.search(rf"Grade\s*{grade}\s*[A-Za-z]+[^A-Za-z0-9]*(\d+)", footer_region)
    if m:
        return int(m.group(1))

    # Pattern 3: "N Grade X Biology" or "N | Grade X Biology" (number before grade/subject)
    m = re.search(rf"(\d+)\s*[|\u2013\u2014\-]?\s*Grade\s*{grade}", footer_region)
    if m:
        return int(m.group(1))

    # Grade 12 prints the page number in the page header (first lines).
    # Pattern 4: standalone number in the first few lines (header)
    for line in lines[:3]:
        line = line.strip()
        if re.match(r"^\d{1,3}$", line):
            n = int(line)
            if 1 <= n <= 600:
                return n

    header_region = "\n".join(lines[:3]).strip()

    # Pattern 5: "Grade X Biology N" (number after grade/subject)
    m = re.search(rf"Grade\s*{grade}\s*[A-Za-z]+[^A-Za-z0-9]*(\d+)", header_region)
    if m:
        return int(m.group(1))

    # Pattern 6: "N Grade X Biology" or "N | Grade X Biology" (number before grade/subject)
    m = re.search(rf"(\d+)\s*[|\u2013\u2014\-]?\s*Grade\s*{grade}", header_region)
    if m:
        return int(m.group(1))

    return max(1, pdf_page_num - FRONT_MATTER_PAGES.get(grade, 3))


def _roman_to_int(s: str) -> int:
    """Convert Roman numeral string to integer. Returns 0 on invalid input."""
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for c in reversed(s):
        val = values.get(c, 0)
        if val < prev:
            total -= val
        else:
            total += val
        prev = val
    return total


def extract_unit(text: str) -> str:
    """Extract unit name from text (e.g. 'Unit 3: Biochemical Molecules')."""
    match = re.search(
        r"\bUnit\s+(\d+|[IVXLCDM]+):\s*([A-Z][A-Za-z\-]*(?:\s+(?:[A-Z][A-Za-z\-]*|[a-z]{2,4})){0,8})",
        text,
        re.IGNORECASE,
    )
    if match and match.start() < 200:
        num_str = match.group(1)
        name = match.group(2).strip()
        if re.search(r"\d+\.\d+", name) or re.search(r"\b\d{2,}\b", name):
            return ""
        name = re.sub(r"\s+", " ", name).strip()
        if 4 < len(name) < 80:
            num = _roman_to_int(num_str.upper()) if num_str.isalpha() else int(num_str)
            return f"Unit {num}: {name}" if num else ""
    match = re.search(
        r"\bUnit\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\s*:\s*([A-Z][A-Za-z\-]*(?:\s+(?:[A-Z][A-Za-z\-]*|[a-z]{2,4})){0,8})",
        text,
    )
    if match and match.start() < 200:
        num_word = match.group(1)
        name = match.group(2).strip()
        if re.search(r"\d+\.\d+", name) or re.search(r"\b\d{2,}\b", name):
            return ""
        name = re.sub(r"\s+", " ", name).strip()
        if 4 < len(name) < 80:
            num_map = {
                "ONE": 1,
                "TWO": 2,
                "THREE": 3,
                "FOUR": 4,
                "FIVE": 5,
                "SIX": 6,
                "SEVEN": 7,
                "EIGHT": 8,
                "NINE": 9,
                "TEN": 10,
            }
            num = num_map.get(num_word.upper(), 0)
            return f"Unit {num}: {name}" if num else ""
    match = re.search(r"\bUNIT\s+([A-Z]+)\s+([A-Z][A-Z\s]{3,60})", text)
    if match and match.start() < 200:
        num_word = match.group(1)
        name = match.group(2).strip()
        if name and not re.search(r"\d+\.\d+", name):
            num_map = {
                "ONE": 1,
                "TWO": 2,
                "THREE": 3,
                "FOUR": 4,
                "FIVE": 5,
                "SIX": 6,
                "SEVEN": 7,
                "EIGHT": 8,
                "NINE": 9,
                "TEN": 10,
            }
            num = num_map.get(num_word.upper(), 0)
            return f"Unit {num}: {name.title()}" if num else ""
    return ""


_SECTION_RE = re.compile(r"(?:^|\n)\s*(\d+\.\d+)(?!\.\d)\s+([A-Z][^\n]{3,80})")
_SUBTOPIC_RE = re.compile(r"(?:^|\n)\s*(\d+\.\d+\.\d+)\s+([A-Z][^\n]{3,80})")


def extract_section_subtopic(text: str) -> tuple[str, str]:
    """Extract (section, subtopic) from text.

    Section examples: '3.1 Carbohydrates'
    Subtopic examples: '3.1.1 Monosaccharides'
    Returns (heading, '') for sections, ('', heading) for subtopics.
    """
    m = _SUBTOPIC_RE.search(text)
    if m:
        return "", f"{m.group(1)} {m.group(2).strip()}"
    m = _SECTION_RE.search(text)
    if m:
        return f"{m.group(1)} {m.group(2).strip()}", ""
    return "", ""


def extract_heading(text: str) -> str:
    """Extract the first line that looks like a heading."""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if line and (line.isupper() or re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:", line)):
            return line[:100]
    return lines[0][:100] if lines else ""
