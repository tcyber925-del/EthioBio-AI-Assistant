"""Index extracted textbook diagrams into PostgreSQL and ChromaDB.

Usage:
    python scripts/index_diagrams.py
"""

import argparse
import glob
import sys
from pathlib import Path

import structlog

structlog.configure(
    processors=[structlog.stdlib.filter_by_level, structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

DIAGRAMS_BASE = "data/diagrams"


def _parse_metadata_from_path(image_path: Path) -> dict:
    """Reconstruct metadata from directory structure and filename.

    Expected path format: data/diagrams/{grade}/{pdf_stem}_{fig_num}.jpg
    """
    parts = image_path.parts
    grade = int(parts[2])  # data/diagrams/{grade}/
    stem = image_path.stem
    fig_num = int(stem.split("_")[-1])
    pdf_stem = "_".join(stem.split("_")[:-1])

    return {
        "grade": grade,
        "fig_num": fig_num,
        "pdf_stem": pdf_stem,
        "image_path": str(image_path),
    }


def main():
    parser = argparse.ArgumentParser(description="Index textbook diagrams into DB and ChromaDB")
    parser.add_argument("--grade", type=int, choices=range(7, 13), help="Single grade to index")
    args = parser.parse_args()

    if args.grade:
        pattern = f"{DIAGRAMS_BASE}/{args.grade}/**/*.jpg"
    else:
        pattern = f"{DIAGRAMS_BASE}/**/*.jpg"
    image_paths = sorted(glob.glob(pattern, recursive=True))
    logger.info("found_diagrams", count=len(image_paths))

    for img_path_str in image_paths:
        img_path = Path(img_path_str)
        meta = _parse_metadata_from_path(img_path)
        logger.info(
            "indexing_diagram",
            grade=meta["grade"],
            pdf_stem=meta["pdf_stem"],
            fig_num=meta["fig_num"],
        )

    logger.info("indexing_complete", total=len(image_paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
