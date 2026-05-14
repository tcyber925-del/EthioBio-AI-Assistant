"""
EthioBio AI Assistant — Curriculum Ingestion Script

Scans data/textbooks/ for PDF and DOCX files organized by grade,
extracts text with PyMuPDF/python-docx, splits into curriculum-aligned
chunks, embeds them, and stores in ChromaDB for RAG retrieval.

Usage:
    python scripts/ingest_curriculum.py                          # Ingest all files
    python scripts/ingest_curriculum.py --stats                  # Show store stats
    python scripts/ingest_curriculum.py --query "What is cell?"  # Test retrieval
    python scripts/ingest_curriculum.py --clear                  # Clear all vectors
"""

import argparse
import os
import re
import sys
import glob
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rag.embedder import Embedder
from src.rag.vector_store import VectorStore
from src.config import settings

TEXTBOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "textbooks")
SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt")


def extract_text_from_pdf(filepath: str) -> list[dict]:
    """Extract text from a PDF file using PyMuPDF.
    Returns list of {text, page_number} dicts.
    """
    import fitz
    pages = []
    doc = fitz.open(filepath)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().strip()
        if text:
            pages.append({"text": text, "page_number": page_num + 1})
    doc.close()
    return pages


def extract_text_from_docx(filepath: str) -> list[dict]:
    """Extract text from a DOCX file using python-docx."""
    from docx import Document
    doc = Document(filepath)
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{"text": full_text, "page_number": 0}]


def detect_source_type(filename: str) -> str:
    """Detect the type of curriculum material from filename."""
    name_lower = filename.lower()
    if "teacher" in name_lower or "guide" in name_lower:
        return "teachers_guide"
    if "workbook" in name_lower or "work" in name_lower:
        return "workbook"
    if "reference" in name_lower or "handbook" in name_lower:
        return "reference"
    if "note" in name_lower or "summary" in name_lower:
        return "teacher_notes"
    return "student_textbook"


def detect_grade_from_path(filepath: str) -> int:
    """Extract grade level from the directory path."""
    match = re.search(r"Grade(\d+)", filepath)
    if match:
        return int(match.group(1))
    return 0


def chunk_text(text: str, source_type: str = "student_textbook") -> list[dict]:
    """Split text into curriculum-aligned chunks at natural boundaries.

    Strategy:
    1. Split on chapter/unit/section headers
    2. Split long sections by paragraphs
    3. Keep chunks between 300-1500 characters
    """
    # Common Ethiopian curriculum header patterns
    header_patterns = [
        r"(?:^|\n)\s*(?:Chapter|Unit|Module)\s+\d+[\.\s:]",
        r"(?:^|\n)\s*\d+\.\d+\s+[A-Z]",
        r"(?:^|\n)\s*[A-Z][A-Z\s]{5,}(?:\n|$)",
        r"(?:^|\n)\s*Lesson\s+\d+",
        r"(?:^|\n)\s*Topic\s+\d+",
        r"(?:^|\n)\s*Session\s+\d+",
        r"(?:^|\n)\s*Part\s+[A-Z0-9]",
        r"(?:^|\n)\s*Section\s+\d+",
    ]

    combined_pattern = "|".join(header_patterns)

    chunks = []

    if source_type == "teachers_guide" or source_type == "teacher_notes":
        paragraphs = re.split(r"\n\s*\n", text)
        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current_chunk) + len(para) > 1500 and current_chunk:
                chunks.append({"text": current_chunk.strip(), "heading": _extract_heading(current_chunk)})
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append({"text": current_chunk.strip(), "heading": _extract_heading(current_chunk)})
    else:
        sections = re.split(combined_pattern, text)
        for section in sections:
            section = section.strip()
            if not section or len(section) < 30:
                continue

            if len(section) > 2000:
                paragraphs = re.split(r"\n\s*\n", section)
                current = ""
                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue
                    if len(current) + len(para) > 1200 and current:
                        chunks.append({"text": current.strip(), "heading": _extract_heading(current)})
                        current = para
                    else:
                        current += "\n\n" + para if current else para
                if current:
                    chunks.append({"text": current.strip(), "heading": _extract_heading(current)})
            else:
                chunks.append({"text": section, "heading": _extract_heading(section)})

    filtered = [c for c in chunks if len(c["text"]) >= 50]
    return filtered


def _extract_heading(text: str) -> str:
    """Extract the first line that looks like a heading."""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if line and (line.isupper() or re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:", line)):
            return line[:100]
    return lines[0][:100] if lines else ""


def scan_files(base_dir: str) -> list[dict]:
    """Scan the textbooks directory for curriculum files organized by grade."""
    files = []
    for grade_dir in sorted(glob.glob(os.path.join(base_dir, "Grade*"))):
        grade = detect_grade_from_path(grade_dir)
        if not grade:
            continue
        for ext in SUPPORTED_EXTENSIONS:
            for fp in sorted(glob.glob(os.path.join(grade_dir, f"*{ext}"))):
                filename = os.path.basename(fp)
                files.append({
                    "filepath": fp,
                    "filename": filename,
                    "grade_level": grade,
                    "source_type": detect_source_type(filename),
                    "extension": ext,
                })
    return files


async def process_file(file_info: dict, embedder: Embedder, store: VectorStore) -> int:
    """Process a single curriculum file: extract, chunk, embed, store."""
    filepath = file_info["filepath"]
    grade = file_info["grade_level"]
    source_type = file_info["source_type"]
    filename = file_info["filename"]

    print(f"  Processing: Grade {grade}/{filename} ({source_type})")

    try:
        if filepath.endswith(".pdf"):
            pages = extract_text_from_pdf(filepath)
        elif filepath.endswith(".docx"):
            pages = extract_text_from_docx(filepath)
        elif filepath.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                pages = [{"text": f.read(), "page_number": 0}]
        else:
            return 0
    except Exception as e:
        print(f"    ❌ Extraction error: {e}")
        return 0

    if not pages or not any(p["text"] for p in pages):
        print(f"    ⚠️  No text extracted")
        return 0

    full_text = "\n\n".join(p["text"] for p in pages)
    chunks = chunk_text(full_text, source_type)

    if not chunks:
        print(f"    ⚠️  No chunks created")
        return 0

    print(f"    Extracted {len(pages)} pages → {len(chunks)} chunks")

    chunk_texts = [c["text"] for c in chunks]
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"g{grade}_{filename}_{i}"
        metadatas.append({
            "grade_level": grade,
            "source_type": source_type,
            "source_file": filename,
            "heading": chunk.get("heading", "") or chunk["text"][:80],
            "chunk_index": i,
        })
        ids.append(chunk_id)

    try:
        embeddings = await embedder.embed_batch(chunk_texts)
        await store.add_documents(
            texts=chunk_texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        print(f"    ✅ Stored {len(chunks)} chunks in ChromaDB")
        return len(chunks)
    except Exception as e:
        print(f"    ❌ Embedding/storage error: {e}")
        return 0


async def main():
    parser = argparse.ArgumentParser(description="Ingest curriculum materials into RAG vector store")
    parser.add_argument("--textbooks-dir", default=TEXTBOOKS_DIR, help="Path to textbooks directory")
    parser.add_argument("--clear", action="store_true", help="Clear all vectors before ingestion")
    parser.add_argument("--stats", action="store_true", help="Show store statistics")
    parser.add_argument("--query", type=str, help="Test retrieval with a query string")
    parser.add_argument("--grade", type=int, help="Filter query by grade level")

    args = parser.parse_args()

    if not os.path.isdir(args.textbooks_dir):
        print(f"❌ Textbooks directory not found: {args.textbooks_dir}")
        print(f"   Create it and place PDFs in: {args.textbooks_dir}/Grade7/ ... Grade12/")
        sys.exit(1)

    embedder = Embedder()
    store = VectorStore()

    if args.clear:
        print("🗑️  Clearing existing vectors...")
        await store.delete_collection()
        print("   Cleared.")

    if args.stats:
        count = store.count()
        print(f"📊 Vector Store Statistics")
        print(f"   Collection: {settings.collection_name}")
        print(f"   Total chunks: {count}")
        print(f"   Persist path: {settings.vector_store_path}")
        return

    if args.query:
        from src.rag.retriever import Retriever
        print(f"🔍 Testing retrieval for: \"{args.query}\"")
        retriever = Retriever(embedder=embedder, vector_store=store)
        results = await retriever.retrieve(
            query=args.query,
            n_results=3,
            grade_level=args.grade,
        )
        print(f"   Retrieved {len(results)} results")
        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            print(f"\n   [{i}] Grade {meta.get('grade_level', '?')} - {meta.get('source_file', '?')}")
            print(f"       {r['content'][:150]}...")
            print(f"       Score: {r.get('score', 0.0):.3f}")
        return

    files = scan_files(args.textbooks_dir)

    if not files:
        print(f"⚠️  No supported files found in {args.textbooks_dir}")
        print(f"   Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
        print(f"   Expected structure:")
        print(f"     {args.textbooks_dir}/Grade7/biology_textbook.pdf")
        print(f"     {args.textbooks_dir}/Grade9/biology_teachers_guide.docx")
        sys.exit(0)

    print(f"📚 Found {len(files)} files to process\n")
    total_chunks = 0
    for f in files:
        chunks = await process_file(f, embedder, store)
        total_chunks += chunks

    count = store.count()
    print(f"\n✅ Ingestion complete!")
    print(f"   Files processed: {len(files)}")
    print(f"   Total chunks stored: {total_chunks}")
    print(f"   ChromaDB collection count: {count}")
    print(f"   Location: {settings.vector_store_path}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
