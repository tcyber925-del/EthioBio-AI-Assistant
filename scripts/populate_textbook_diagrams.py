"""Populate textbook_diagrams table from extracted page images.

Scans diagram_output/{grade}/ for extracted JPGs and creates
TextbookDiagram records in PostgreSQL.

Usage:
    python scripts/populate_textbook_diagrams.py                     # all grades
    python scripts/populate_textbook_diagrams.py --grade 10          # single grade
    python scripts/populate_textbook_diagrams.py --dry-run           # preview only
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path
from typing import Optional

import structlog
from sqlalchemy import select

from src.database.models import TextbookDiagram
from src.database.session import get_session

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

OUTPUT_ROOT = Path("diagram_output")
PAGE_PATTERN = re.compile(r"(.+)_page_(\d+)\.jpg$")


def scan_pages(grade: int) -> list[dict]:
    """Scan output directory for extracted page images."""
    grade_dir = OUTPUT_ROOT / str(grade)
    if not grade_dir.exists():
        logger.info("grade_dir_not_found", grade=grade, path=str(grade_dir))
        return []

    records = []
    for img_path in sorted(grade_dir.glob("*.jpg")):
        m = PAGE_PATTERN.match(img_path.name)
        if not m:
            continue

        pdf_stem = m.group(1)
        page_num = int(m.group(2))

        records.append({
            "grade_level": grade,
            "unit": "",
            "topic": "",
            "caption": "",
            "image_path": str(img_path),
            "figure_number": page_num,
            "page_number": page_num,
            "source_file": f"{pdf_stem}.pdf",
        })

    logger.info("grade_scanned", grade=grade, records=len(records))
    return records


async def populate(
    grade: Optional[int] = None,
    dry_run: bool = False,
    clear: bool = False,
) -> dict:
    """Insert page records into textbook_diagrams table.

    Returns dict with inserted, skipped counts.
    """
    if grade:
        grades = [grade]
    else:
        grades = list(range(7, 13))

    total_inserted = 0
    total_skipped = 0

    for g in grades:
        records = scan_pages(g)
        if not records:
            continue

        if dry_run:
            logger.info(
                "dry_run",
                grade=g,
                count=len(records),
                first=records[0]["image_path"],
                last=records[-1]["image_path"],
            )
            continue

        async for session in get_session():  # type: ignore[attr-defined]
            if clear:
                existing = await session.execute(
                    select(TextbookDiagram).where(TextbookDiagram.grade_level == g)
                )
                for row in existing.scalars():
                    await session.delete(row)
                await session.commit()
                logger.info("cleared_grade", grade=g)

            existing_stmt = select(TextbookDiagram).where(
                TextbookDiagram.grade_level == g,
                TextbookDiagram.source_file == records[0]["source_file"],
            )
            existing_result = await session.execute(existing_stmt)
            existing_fig_nums = {r.figure_number for r in existing_result.scalars()}

            inserted = 0
            skipped = 0
            for rec in records:
                if rec["figure_number"] in existing_fig_nums:
                    skipped += 1
                    continue

                diagram = TextbookDiagram(
                    grade_level=rec["grade_level"],
                    unit=rec["unit"],
                    topic=rec["topic"],
                    caption=rec["caption"],
                    image_path=rec["image_path"],
                    figure_number=rec["figure_number"],
                    page_number=rec["page_number"],
                    source_file=rec["source_file"],
                )
                session.add(diagram)
                inserted += 1

            await session.commit()
            total_inserted += inserted
            total_skipped += skipped
            logger.info("grade_done", grade=g, inserted=inserted, skipped=skipped)

    return {"inserted": total_inserted, "skipped": total_skipped}


def main():
    parser = argparse.ArgumentParser(description="Populate textbook_diagrams from extracted pages")
    parser.add_argument("--grade", type=int, choices=range(7, 13), help="Single grade to process")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--clear", action="store_true",
                        help="Clear existing records for grade before inserting")
    args = parser.parse_args()

    outcome = asyncio.run(populate(
        grade=args.grade,
        dry_run=args.dry_run,
        clear=args.clear,
    ))
    logger.info("populate_complete", **outcome)
    return 0 if outcome["inserted"] > 0 or outcome["skipped"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
