"""Extract textbook figures from all Ethiopian biology PDFs.

Usage:
    python scripts/ingest_diagrams.py          # process all grades
    python scripts/ingest_diagrams.py --grade 9 # single grade
"""

import argparse
import sys
from pathlib import Path

import structlog

from src.ingestion.diagram_extractor import extract_figures_from_pdf

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

PDF_GLOB = "data/textbooks/Grade{grade}/*.pdf"


def process_grade(grade: int) -> int:
    """Extract figures from all PDFs for a grade. Returns total figure count."""
    pattern = PDF_GLOB.format(grade=grade)
    pdfs = sorted(Path().glob(pattern))

    if not pdfs:
        logger.info("grade_no_pdfs_found", grade=grade)
        return 0

    total = 0
    for pdf_path in pdfs:
        try:
            figures = extract_figures_from_pdf(str(pdf_path), grade=grade)
            logger.info(
                "grade_pdf_done",
                grade=grade,
                pdf=pdf_path.name,
                figure_count=len(figures),
            )
            total += len(figures)
        except Exception:
            logger.exception("grade_pdf_error", grade=grade, pdf=pdf_path.name)
    return total


def main():
    parser = argparse.ArgumentParser(description="Extract textbook figures from biology PDFs")
    parser.add_argument("--grade", type=int, choices=range(7, 13), help="Single grade to process")
    args = parser.parse_args()

    if args.grade:
        grades = [args.grade]
    else:
        grades = list(range(7, 13))

    grand_total = 0
    for grade in grades:
        count = process_grade(grade)
        grand_total += count
        logger.info("grade_summary", grade=grade, figure_count=count)

    logger.info("extraction_complete", total_figures=grand_total)
    return grand_total


if __name__ == "__main__":
    sys.exit(main())
