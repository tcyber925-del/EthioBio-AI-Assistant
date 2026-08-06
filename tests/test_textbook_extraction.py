from unittest.mock import MagicMock

from src.ingestion.textbook import (
    extract_heading,
    extract_page_number,
    extract_pdf_pages,
    extract_section_subtopic,
    extract_unit,
)


class TestExtractPageNumber:
    def test_footer_standalone_number(self):
        text = "Some body text.\n\n42"
        assert extract_page_number(text, pdf_page_num=45, grade=10) == 42

    def test_footer_grade_biology_number_after(self):
        text = "body\nGrade 10 Biology 47"
        assert extract_page_number(text, pdf_page_num=50, grade=10) == 47

    def test_footer_grade_biology_number_before(self):
        text = "body\n47 | Grade 10 Biology"
        assert extract_page_number(text, pdf_page_num=50, grade=10) == 47

    def test_header_standalone_number_grade12(self):
        text = "12\nSome body text."
        assert extract_page_number(text, pdf_page_num=17, grade=12) == 12

    def test_front_matter_fallback(self):
        text = "Some body text without a page number."
        assert extract_page_number(text, pdf_page_num=50, grade=10) == 47

    def test_unknown_grade_uses_pdf_index(self):
        text = "Some body text."
        assert extract_page_number(text, pdf_page_num=9, grade=0) == 9

    def test_out_of_range_ignored(self):
        text = "body\n9999"
        assert extract_page_number(text, pdf_page_num=20, grade=10) == 17


class TestExtractUnit:
    def test_extract_unit_arabic(self):
        text = "Unit 3: Biochemical Molecules.\nbody text"
        assert extract_unit(text) == "Unit 3: Biochemical Molecules"

    def test_extract_unit_roman(self):
        text = "Unit I: Sub-fields of Biology.\nbody text"
        assert extract_unit(text) == "Unit 1: Sub-fields of Biology"

    def test_extract_unit_word_numeral(self):
        text = "UNIT FOUR GENETICS\nsome body"
        assert extract_unit(text) == "Unit 4: Genetics"


class TestExtractHeadingSection:
    def test_extract_heading_uppercase(self):
        assert extract_heading("THE CELL\nbody text") == "THE CELL"

    def test_extract_heading_first_line_fallback(self):
        assert extract_heading("Some plain first line\nmore") == "Some plain first line"

    def test_extract_section_subtopic(self):
        # When a subtopic heading is present, legacy behavior reports it first
        sec, sub = extract_section_subtopic(
            "3.1 Carbohydrates\n\n3.1.1 Monosaccharides\nbody text"
        )
        assert sec == ""
        assert sub == "3.1.1 Monosaccharides"

    def test_extract_section_with_subtopic_heading_only(self):
        sec, sub = extract_section_subtopic("3.1 Carbohydrates\n\nbody text")
        assert sec == "3.1 Carbohydrates"
        assert sub == ""

    def test_extract_section_only(self):
        sec, sub = extract_section_subtopic("3.2 Lipids\nbody text")
        assert sec == "3.2 Lipids"
        assert sub == ""


class TestExtractPdfPages:
    def test_extract_pdf_pages_1_based_and_skips_empty(self, monkeypatch):
        fake_reader = MagicMock()
        fake_reader.pages = [
            MagicMock(extract_text=MagicMock(return_value="page one text")),
            MagicMock(extract_text=MagicMock(return_value="")),
            MagicMock(extract_text=MagicMock(return_value="page three text")),
        ]
        monkeypatch.setattr("pypdf.PdfReader", lambda path: fake_reader)

        pages = extract_pdf_pages("/phony/doc.pdf")
        assert len(pages) == 2
        assert pages[0] == {"text": "page one text", "pdf_page": 1}
        assert pages[1] == {"text": "page three text", "pdf_page": 3}
