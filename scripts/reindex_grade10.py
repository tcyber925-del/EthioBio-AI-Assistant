"""
Re-index Grade 10 textbook with page-number metadata into pgvector.

Run with prod DB override (DATABASE_URL=... OPENROUTER_API_KEY=...):
  python scripts/reindex_grade10.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/app")  # container root; harmless locally

from src.config import settings
from src.ingestion.textbook import (
    extract_heading,
    extract_page_number,
    extract_pdf_pages,
    extract_section_subtopic,
    extract_unit,
)
from src.rag.embedder import Embedder
from src.rag.pgvector_store import PGVectorStore

KO_ID = "9c993dfe-8f9a-404c-9229-451548aa70f9"
GRADE = 10
SOURCE_FILE = "Biology Grade 10 ST (MT)(BOOK).pdf"
PDF_PATH = Path("data/textbooks/Grade10/Biology Grade 10 ST (MT)(BOOK).pdf")


def chunk_text(text: str, max_chars: int = 1500) -> list[dict]:
    """Mirror src.core.pipeline.service._chunk_text (paragraph-level split)."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) <= max_chars:
            chunks.append({"text": para})
        else:
            sentences = para.replace("\n", " ").split(". ")
            buf = ""
            for sent in sentences:
                candidate = f"{buf}. {sent}".strip() if buf else sent
                if len(candidate) > max_chars and buf:
                    chunks.append({"text": buf + "."})
                    buf = sent
                else:
                    buf = candidate
            if buf:
                chunks.append({"text": buf})
    return chunks


async def main():
    store = PGVectorStore(collection_name=settings.collection_name)
    deleted = await store.delete_by_grade(GRADE)
    print(f"Deleted {deleted} grade-10 embeddings")

    pages = extract_pdf_pages(str(PDF_PATH))
    print(f"Extracted {len(pages)} pages")
    if not pages:
        raise SystemExit("No pages extracted — check the PDF path")

    chunks = []
    for page in pages:
        for c in chunk_text(page["text"]):
            c["page_number"] = extract_page_number(page["text"], page["pdf_page"], GRADE)
            c["pdf_page"] = page["pdf_page"]
            chunks.append(c)

    filtered = [c for c in chunks if len(c["text"]) >= 80]
    print(f"{len(chunks)} raw chunks, {len(filtered)} after quality filter")

    metadatas, texts = [], []
    for i, c in enumerate(filtered):
        if not c.get("unit"):
            c["unit"] = extract_unit(c["text"])
        if not c.get("heading"):
            c["heading"] = extract_heading(c["text"])
        sec, sub = extract_section_subtopic(c["text"])
        c["section"] = c.get("section") or sec
        c["subtopic"] = c.get("subtopic") or sub
        metadatas.append(
            {
                "knowledge_object_id": KO_ID,
                "chunk_index": i,
                "heading": c["heading"] or c["text"][:80],
                "topic": c.get("topic") or "",
                "grade_level": GRADE,
                "unit": c.get("unit") or "",
                "section": c.get("section") or "",
                "subtopic": c.get("subtopic") or "",
                "source_type": "student_textbook",
                "source_file": SOURCE_FILE,
                "page_number": c["page_number"],
            }
        )
        texts.append(c["text"])

    embedder = Embedder()
    embeddings = await embedder.embed_batch(texts)
    ids = [f"g10_{SOURCE_FILE}_{i}" for i in range(len(texts))]
    await store.add_documents(texts, embeddings, metadatas, ids)

    covered = sum(1 for m in metadatas if m["page_number"] > 0)
    print(f"Stored {len(texts)} chunks; page_number>0 on {covered}/{len(metadatas)}")
    for m, t in list(zip(metadatas, texts, strict=False))[:3]:
        print("  sample:", m["page_number"], m["source_file"], t[:40])


if __name__ == "__main__":
    asyncio.run(main())
