"""Index textbook diagram captions into ChromaDB for RAG retrieval.

Usage:
    python scripts/index_diagrams.py                     # all grades
    python scripts/index_diagrams.py --grade 10          # single grade
    python scripts/index_diagrams.py --dry-run            # preview only
"""

import argparse
import asyncio
import sys
from typing import Optional

import structlog
from sqlalchemy import select

from src.database.models import TextbookDiagram
from src.retrieval.adapter import VectorStoreAdapter

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()


async def index_diagram_captions(
    records: list[TextbookDiagram],
    adapter: VectorStoreAdapter | None = None,
    dry_run: bool = False,
) -> dict:
    """Embed and upsert diagram captions into ChromaDB.

    Args:
        records: List of TextbookDiagram records to index.
        adapter: VectorStoreAdapter instance (created if None).
        dry_run: If True, log what would be indexed without writing.

    Returns:
        dict with indexed, skipped counts.
    """
    own_adapter = adapter is None
    if own_adapter:
        adapter = VectorStoreAdapter()
    assert adapter is not None

    try:
        texts = []
        metadatas = []
        ids = []
        skipped = 0

        for record in records:
            if not record.caption or not record.caption.strip():
                skipped += 1
                continue

            texts.append(f"[Grade {record.grade_level}] {record.caption}")
            metadatas.append({
                "source_type": "textbook_diagram",
                "grade_level": record.grade_level,
                "unit": record.unit or "",
                "topic": record.topic or "",
                "figure_number": record.figure_number,
                "image_path": record.image_path,
            })
            ids.append(f"diagram_caption_{record.id}")

        if dry_run or not texts:
            if dry_run:
                for i, t in enumerate(texts):
                    logger.info("dry_run_document", index=i, text=t[:100], meta=metadatas[i])
            return {"indexed": 0, "skipped": len(records)}

        embeddings = await adapter.embedder.embed_batch(texts)
        await adapter.vector_store.add_documents(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        return {"indexed": len(texts), "skipped": skipped}
    finally:
        if own_adapter:
            if hasattr(adapter, 'close'):
                adapter.close()


async def main_async(grade: Optional[int] = None, dry_run: bool = False):
    from src.database.session import get_session

    async for session in get_session():  # type: ignore[attr-defined]
        stmt = select(TextbookDiagram)
        if grade is not None:
            stmt = stmt.where(TextbookDiagram.grade_level == grade)
        stmt = stmt.order_by(TextbookDiagram.grade_level, TextbookDiagram.figure_number)

        result = await session.execute(stmt)
        records = list(result.scalars().all())
        logger.info("records_loaded", count=len(records), grade=grade or "all")

        outcome = await index_diagram_captions(records, dry_run=dry_run)
        logger.info(
            "indexing_complete",
            indexed=outcome["indexed"],
            skipped=outcome["skipped"],
            total=len(records),
        )
        return outcome


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Index textbook diagram captions into ChromaDB for RAG retrieval"
    )
    parser.add_argument(
        "--grade", type=int, choices=range(7, 13),
        help="Single grade to process",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Log what would be indexed without writing to ChromaDB",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    asyncio.run(main_async(grade=args.grade, dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
