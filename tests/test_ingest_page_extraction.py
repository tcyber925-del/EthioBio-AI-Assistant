"""Regression tests for `_extract_page_number` in scripts/ingest_curriculum.py.

Ethiopian textbooks print the page number in the footer for grades 9/10/11 and
in the page header for grade 12. The extractor must return the PRINTED page
number so the vector store can drop display-time PAGE_OFFSET corrections.
"""

from scripts.ingest_curriculum import (
    _FRONT_MATTER_PAGES,
    _extract_page_number,
)


class TestFooterExtraction:
    """Grades 9/10/11 print the page number in the page footer."""

    def test_grade_11_standalone_number_in_footer(self):
        # Grade 11: last line of the footer is the printed page number.
        page = "Some body text.\nBIOLOGY GRADE 11\nFDRE-MoE ETHIOPIA\n41\n"
        assert _extract_page_number(page, 51, 11) == 41

    def test_grade_9_standalone_number_in_footer(self):
        page = "Body text that goes on.\n44\nGrade 9 Biology\nUnit Three: Cells\n"
        assert _extract_page_number(page, 51, 9) == 44

    def test_grade_subject_number_after_pattern(self):
        # "Grade 9 Biology 4" — number after grade/subject.
        page = "Content line\nGrade 9 Biology 4\n"
        assert _extract_page_number(page, 11, 9) == 4

    def test_number_grade_subject_before_pattern(self):
        # "4 | Grade 9 Biology" — number before grade/subject.
        page = "Content line\n4 | Grade 9 Biology\n"
        assert _extract_page_number(page, 11, 9) == 4


class TestHeaderExtraction:
    """Grade 12 prints the page number in the page header (first lines)."""

    def test_grade_12_standalone_number_in_header(self):
        page = "254\nUnit 5: Behaviour\nGrade 12\nbody text...\n"
        assert _extract_page_number(page, 259, 12) == 254

    def test_grade_12_header_number_preferred_over_body_numbers(self):
        # A number deep in the body must not win over the header page number.
        page = "131\nUNIT 3: Genetics\nGrade 12\nsome figure 2024 content\n"
        assert _extract_page_number(page, 136, 12) == 131


class TestFallback:
    def test_fallback_uses_grade_specific_front_matter(self):
        # No extractable number: estimate from PDF index and front-matter count.
        assert _extract_page_number("plain body text, no numbers", 10, 12) == 5
        assert _extract_page_number("plain body text, no numbers", 10, 9) == 3
        assert _extract_page_number("plain body text, no numbers", 10, 11) == 1

    def test_front_matter_map_covers_all_grades(self):
        assert _FRONT_MATTER_PAGES == {9: 7, 10: 3, 11: 10, 12: 5}

    def test_fallback_unknown_grade_defaults_to_three(self):
        assert _extract_page_number("plain body text", 10, 7) == 7

    def test_fallback_clamped_to_one(self):
        assert _extract_page_number("plain body text", 3, 12) == 1

    def test_empty_page_uses_fallback(self):
        assert _extract_page_number("", 10, 12) == 5

    def test_out_of_range_number_ignored(self):
        # A standalone 4-digit number is not a textbook page number.
        page = "Unit 4: Evolution\n2024\nbody text\n"
        assert _extract_page_number(page, 40, 12) == 40 - _FRONT_MATTER_PAGES[12]
