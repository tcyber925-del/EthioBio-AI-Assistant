"""
Docling-based PDF extractor for Ethiopian biology textbooks.

Uses PyPdfium2 for fast text extraction, with Docling + RapidOCR fallback
for pages with font encoding issues. Produces clean, structured text with
hierarchical chunking optimized for RAG.
"""

import structlog
from typing import Optional
from pathlib import Path

logger = structlog.get_logger()


def _is_garbled(text: str, alpha_threshold: float = 0.40) -> bool:
    """Detect if a page has garbled text based on alphabetic character ratio.

    Garbled pages from font encoding issues have very low alphabetic character
    ratios (<40%) because most characters are control codes or encoding artifacts.

    Args:
        text: The extracted page text.
        alpha_threshold: Minimum fraction of alphabetic chars for clean text.

    Returns:
        True if the text appears garbled.
    """
    if not text or len(text) < 50:
        return False
    alpha = sum(1 for c in text if c.isalpha())
    return (alpha / len(text)) < alpha_threshold


def extract_with_docling(
    filepath: str,
    use_ocr: bool = False,
    rapidocr_fallback: bool = True,
) -> list[dict]:
    """Extract text from PDF using PyPdfium2 with optional RapidOCR fallback.

    Args:
        filepath: Path to the PDF file.
        use_ocr: If True, forces full-page OCR on all pages via RapidOCR.
        rapidocr_fallback: If True, re-processes garbled pages with RapidOCR.

    Returns:
        List of {text: str, page_number: int, heading: str} dicts.
    """
    if use_ocr:
        return _extract_with_full_ocr(filepath)

    # Fast extraction with PyPdfium2
    import pypdfium2 as pdfium

    pages = []
    garbled_pages = []

    doc = pdfium.PdfDocument(filepath)
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_textpage().get_text_bounded().strip()
        page_num = i + 1
        if text:
            pages.append({
                "text": text,
                "page_number": page_num,
                "heading": _extract_heading(text),
            })
            if rapidocr_fallback and _is_garbled(text):
                garbled_pages.append(page_num)
    doc.close()

    # If most pages are garbled, use full OCR instead
    garbled_ratio = len(garbled_pages) / len(pages) if pages else 0
    if garbled_ratio > 0.50 and rapidocr_fallback:
        logger.info(
            "most_pages_garbled",
            filepath=Path(filepath).name,
            garbled=len(garbled_pages),
            total=len(pages),
        )
        return _extract_with_full_ocr(filepath)

    if garbled_pages and rapidocr_fallback:
        logger.info(
            "garbled_pages_detected",
            filepath=Path(filepath).name,
            garbled_pages=garbled_pages,
        )
        ocr_pages = _extract_garbled_pages_with_ocr(filepath, garbled_pages)
        for ocr_page in ocr_pages:
            for i, p in enumerate(pages):
                if p["page_number"] == ocr_page["page_number"]:
                    pages[i] = ocr_page
                    break

    logger.info("docling_extraction_complete", filepath=Path(filepath).name, pages=len(pages))
    return pages


def _extract_with_full_ocr(filepath: str) -> list[dict]:
    """Extract text from PDF using pypdfium2 + RapidOCR.

    Renders PDF pages as images and runs OCR on them. Much faster than Docling
    for OCR-only extraction since it avoids loading layout models.

    Args:
        filepath: Path to the PDF file.

    Returns:
        List of {text: str, page_number: int, heading: str} dicts.
    """
    import pypdfium2 as pdfium
    from rapidocr import RapidOCR

    ocr = RapidOCR()
    doc = pdfium.PdfDocument(filepath)
    pages = []

    for i in range(len(doc)):
        page = doc[i]
        image = page.render(scale=1.0)  # scale=1.0 is faster, good enough for text
        bitmap = image.to_numpy()
        page_num = i + 1

        result = ocr(bitmap)
        if result.txts:
            text = " ".join(result.txts).strip()
            if text:
                pages.append({
                    "text": text,
                    "page_number": page_num,
                    "heading": _extract_heading(text),
                })

    doc.close()
    return pages


def _extract_garbled_pages_with_ocr(filepath: str, page_numbers: list[int]) -> list[dict]:
    """Re-extract specific pages using pypdfium2 + RapidOCR.

    Args:
        filepath: Path to the PDF file.
        page_numbers: List of 1-based page numbers to re-extract.

    Returns:
        List of {text: str, page_number: int, heading: str} dicts.
    """
    import pypdfium2 as pdfium
    from rapidocr import RapidOCR

    ocr = RapidOCR()
    doc = pdfium.PdfDocument(filepath)
    ocr_pages = []

    for i in range(len(doc)):
        page_num = i + 1
        if page_num not in page_numbers:
            continue

        page = doc[i]
        image = page.render(scale=1.0)
        bitmap = image.to_numpy()

        result = ocr(bitmap)
        if result.txts:
            text = " ".join(result.txts).strip()
            if text:
                ocr_pages.append({
                    "text": text,
                    "page_number": page_num,
                    "heading": _extract_heading(text),
                })
                logger.info("ocr_fallback_applied", page=page_num)

    doc.close()
    return ocr_pages


def chunk_with_docling(filepath: str, max_tokens: int = 512) -> list[dict]:
    """Extract and chunk a PDF using Docling's HybridChunker.

    This is the recommended approach for RAG: preserves document structure
    and creates token-aware chunks aligned with the embedding model.

    Args:
        filepath: Path to the PDF file.
        max_tokens: Maximum tokens per chunk.

    Returns:
        List of {text: str, page_number: int, heading: str} dicts.
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.chunking import HybridChunker
    from transformers import AutoTokenizer
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
    )
    pipeline_options.ocr_options = RapidOcrOptions(
        force_full_page_ocr=True,
        lang=["english"],
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend,
            )
        }
    )

    result = converter.convert(filepath)
    doc = result.document

    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    chunker = HybridChunker(
        tokenizer=tokenizer,
        max_tokens=max_tokens,
        merge_peers=True,
    )

    chunks = []
    for chunk in chunker.chunk(doc):
        contextualized = chunker.contextualize(chunk)
        page_num = chunk.meta.doc_items[0].prov[0].page_no + 1 if chunk.meta.doc_items else 0

        chunks.append({
            "text": contextualized,
            "page_number": page_num,
            "heading": _extract_heading(contextualized),
        })

    logger.info("docling_chunking_complete", filepath=Path(filepath).name, chunks=len(chunks))
    return chunks


def _extract_heading(text: str) -> str:
    """Extract the first meaningful line as a heading."""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) > 10 and len(line) < 200:
            return line[:100]
    return lines[0][:100] if lines else ""
