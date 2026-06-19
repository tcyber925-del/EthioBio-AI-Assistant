"""Extract all pages from textbook PDFs as JPG images.

Renders each PDF page at 150 DPI using pypdfium2 and saves as JPEG.
Faster and more reliable than Docling-based figure extraction for scanned PDFs.

Usage:
    python scripts/extract_pages.py                     # all grades
    python scripts/extract_pages.py --grade 9           # single grade
    python scripts/extract_pages.py --grade 10 --dpi 200
"""

import argparse
import sys
from pathlib import Path

import pypdfium2 as pdfium
import structlog

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

PDF_GLOB = "data/textbooks/Grade{grade}/*.pdf"
OUTPUT_ROOT = "diagram_output"
JPEG_QUALITY = 85


def extract_pages_from_pdf(filepath: str, grade: int, dpi: float = 150) -> list[dict]:
    """Render every page of a PDF as a JPEG image.

    Returns list of dicts with keys:
    image_path, grade, page_num, source_file
    """
    filepath = str(Path(filepath).resolve())
    pdf_stem = Path(filepath).stem
    output_dir = Path(OUTPUT_ROOT) / str(grade)
    output_dir.mkdir(parents=True, exist_ok=True)

    with pdfium.PdfDocument(filepath) as doc:
        total_pages = len(doc)
        extracted = []

        for page_num in range(1, total_pages + 1):
            page = doc[page_num - 1]
            scale = dpi / 72.0
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()

            output_path = output_dir / f"{pdf_stem}_page_{page_num:03d}.jpg"
            pil_image.save(str(output_path), "JPEG", quality=JPEG_QUALITY)

            extracted.append({
                "image_path": str(output_path),
                "grade": grade,
                "page_num": page_num,
                "source_file": Path(filepath).name,
                "total_pages": total_pages,
            })

        logger.info("pdf_done", grade=grade, pdf=Path(filepath).name, pages=total_pages)

    return extracted


def process_grade(grade: int, dpi: float = 150) -> int:
    """Extract pages from all PDFs for a grade. Returns total page count."""
    pattern = PDF_GLOB.format(grade=grade)
    pdfs = sorted(Path().glob(pattern))

    if not pdfs:
        logger.info("grade_no_pdfs_found", grade=grade)
        return 0

    total = 0
    for pdf_path in pdfs:
        try:
            pages = extract_pages_from_pdf(str(pdf_path), grade=grade, dpi=dpi)
            total += len(pages)
        except Exception:
            logger.exception("pdf_error", grade=grade, pdf=pdf_path.name)
    return total


def main():
    parser = argparse.ArgumentParser(description="Extract textbook pages as JPEG images")
    parser.add_argument("--grade", type=int, choices=range(7, 13), help="Single grade to process")
    parser.add_argument("--dpi", type=float, default=150, help="Rendering DPI (default: 150)")
    args = parser.parse_args()

    if args.grade:
        grades = [args.grade]
    else:
        grades = list(range(7, 13))

    grand_total = 0
    for grade in grades:
        count = process_grade(grade, dpi=args.dpi)
        grand_total += count
        logger.info("grade_summary", grade=grade, pages=count)

    logger.info("extraction_complete", total_pages=grand_total)
    return grand_total


if __name__ == "__main__":
    sys.exit(main())
