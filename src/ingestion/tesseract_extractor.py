"""Tesseract-based OCR extraction for Ethiopian biology textbooks.

Handles mixed English + Amharic pages by using Tesseract's script-level
language support. Includes image preprocessing for better accuracy.
"""

import io
from pathlib import Path

import structlog
from PIL import Image, ImageEnhance, ImageFilter

logger = structlog.get_logger()

# Tesseract configuration for mixed English + Ethiopic with LSTM engine
# OEM 3 = LSTM + Legacy, PSM 3 = automatic page segmentation
TESSERACT_CONFIG = "--oem 3 --psm 3 -l eng+script/Ethiopic"
RENDER_DPI = 300


def _preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess a PIL image for better Tesseract accuracy.

    Steps: grayscale → contrast enhance → sharpen → binarize.
    """
    img = image.convert("L")

    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)

    img = img.filter(ImageFilter.SHARPEN)

    img = img.point(lambda x: 0 if x < 128 else 255, "1")

    return img


def extract_page_with_tesseract(image: Image.Image) -> str:
    """Run Tesseract OCR on a single page image with English + Ethiopic support."""
    import pytesseract

    processed = _preprocess_image(image)
    text = pytesseract.image_to_string(processed, config=TESSERACT_CONFIG)
    return text.strip()


def extract_pdf_with_tesseract(filepath: str | Path) -> list[dict]:
    """Extract all pages from a PDF using Tesseract OCR.

    Renders each page at RENDER_DPI, preprocesses, and runs Tesseract
    with English + Ethiopic language support.

    Args:
        filepath: Path to the PDF file.

    Returns:
        List of {text: str, page_number: int} dicts.
    """
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(filepath)
    pages = len(pdf)
    results: list[dict] = []

    logger.info("tesseract_ocr_started", filepath=str(filepath), pages=pages)

    for i in range(pages):
        page = pdf[i]
        bitmap = page.render(scale=RENDER_DPI / 72)

        pil_image = Image.open(io.BytesIO(bitmap.encode("png")))

        text = extract_page_with_tesseract(pil_image)

        if text:
            quality_score = _estimate_quality(text)
            logger.debug(
                "page_ocr_complete",
                page=i + 1,
                chars=len(text),
                quality=quality_score,
            )
        else:
            logger.warning("page_ocr_empty", page=i + 1)

        results.append({"text": text, "page_number": i + 1})

    pdf.close()
    logger.info("tesseract_ocr_complete", filepath=str(filepath), pages=pages)
    return results


def _estimate_quality(text: str) -> float:
    """Estimate OCR text quality based on word-level heuristics.

    Returns a score 0.0-1.0 based on:
    - Proportion of alphanumeric characters
    - Average word length
    - Presence of common English words
    """
    if not text or len(text) < 20:
        return 0.0

    alpha_ratio = sum(1 for c in text if c.isalpha()) / len(text)

    words = text.split()
    avg_word_len = sum(len(w) for w in words) / max(len(words), 1)

    common_words = {"the", "is", "are", "of", "in", "and", "to", "for", "cell", "dna", "rna"}
    common_ratio = sum(1 for w in words if w.lower() in common_words) / max(len(words), 1)

    ethiopic_ratio = sum(1 for c in text if "\u1200" <= c <= "\u137f") / max(len(text), 1)

    score = (
        0.4 * alpha_ratio + 0.3 * min(1.0, avg_word_len / 6.0) + 0.3 * min(1.0, common_ratio * 10)
    )

    if ethiopic_ratio > 0.1:
        score *= 1.2

    return min(1.0, score)
