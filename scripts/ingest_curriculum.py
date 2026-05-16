"""
EthioBio AI Assistant — Curriculum Ingestion Script (Docling + OCR)

Scans data/textbooks/ for PDF files organized by grade,
extracts text with Docling (full-page OCR to bypass font encoding issues),
chunks using HybridChunker for token-aware RAG-optimized chunks,
embeds them, and stores in ChromaDB for retrieval.

Usage:
    python scripts/ingest_curriculum.py                          # Ingest all files with Docling OCR
    python scripts/ingest_curriculum.py --stats                  # Show store stats
    python scripts/ingest_curriculum.py --query "What is cell?"  # Test retrieval
    python scripts/ingest_curriculum.py --clear                  # Clear all vectors
    python scripts/ingest_curriculum.py --use-pymupdf            # Use PyMuPDF instead of Docling
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


def extract_text_from_pdf(filepath: str, use_docling: bool = True) -> list[dict]:
    """Extract text from a PDF file.

    Uses Docling with full-page OCR by default to bypass font encoding issues.
    Falls back to PyMuPDF if use_docling=False.
    """
    if use_docling:
        return _extract_with_docling(filepath)
    return _extract_with_pymupdf(filepath)


def _extract_with_docling(filepath: str) -> list[dict]:
    """Extract text using PyPdfium2 with RapidOCR fallback for garbled pages.

    If more than 50% of pages are garbled, uses full OCR instead.
    """
    import pypdfium2 as pdfium

    pages = []
    garbled_pages = []

    doc = pdfium.PdfDocument(filepath)
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_textpage().get_text_bounded().strip()
        page_num = i + 1
        if text:
            pages.append({"text": text, "page_number": page_num})
            if _is_garbled(text):
                garbled_pages.append(page_num)
    doc.close()

    # If most pages are garbled, use full OCR instead
    garbled_ratio = len(garbled_pages) / len(pages) if pages else 0
    if garbled_ratio > 0.50:
        print(f"    Most pages garbled ({len(garbled_pages)}/{len(pages)}), using full OCR...")
        return _extract_with_ocr(filepath)

    if garbled_pages:
        print(f"    Garbled pages detected: {garbled_pages}, applying RapidOCR fallback...")
        ocr_pages = _extract_with_ocr(filepath, garbled_pages)
        for ocr_page in ocr_pages:
            for i, p in enumerate(pages):
                if p["page_number"] == ocr_page["page_number"]:
                    pages[i] = ocr_page
                    break

    return pages


def _is_garbled(text: str, alpha_threshold: float = 0.40) -> bool:
    """Detect if text has garbled content based on alphabetic character ratio."""
    if not text or len(text) < 50:
        return False
    alpha = sum(1 for c in text if c.isalpha())
    return (alpha / len(text)) < alpha_threshold


def _extract_with_ocr(filepath: str, page_numbers: list[int] | None = None) -> list[dict]:
    """Extract text using pypdfium2 + RapidOCR (bypasses Docling overhead).

    Renders PDF pages as images and runs OCR on them. Much faster than Docling
    for OCR-only extraction since it avoids loading layout models.
    """
    import pypdfium2 as pdfium
    from rapidocr import RapidOCR

    ocr = RapidOCR()
    doc = pdfium.PdfDocument(filepath)
    pages = []

    for i in range(len(doc)):
        page_num = i + 1
        if page_numbers is not None and page_num not in page_numbers:
            continue

        page = doc[i]
        image = page.render(scale=1.0)  # scale=1.0 is faster, good enough for text
        bitmap = image.to_numpy()

        result = ocr(bitmap)
        if result.txts:
            text = " ".join(result.txts).strip()
            if text:
                pages.append({"text": text, "page_number": page_num})

    doc.close()
    return pages


def _extract_with_pymupdf(filepath: str) -> list[dict]:
    """Extract text using PyMuPDF (fallback)."""
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


def _extract_unit(text: str) -> str:
    """Extract unit name from text (e.g. 'Unit 3: Biochemical Molecules')."""
    match = re.search(r"Unit\s+(\d+):\s*([A-Z][^\n]{3,60})", text)
    if match:
        name = match.group(2).strip()
        # Reject TOC entries: contain section refs like '1.1', '1.2', or page numbers
        if re.search(r'\d+\.\d+', name):
            return ""
        if re.search(r'\b\d{2,}\b', name):
            return ""
        name = re.split(r'\s{2,}|\t', name)[0].strip()
        if len(name) < 80:
            return f"Unit {match.group(1)}: {name}"
    return ""


def _extract_topic(text: str) -> str:
    """Extract topic/section heading from text."""
    patterns = [
        r"(?:^|\n)\s*(\d+\.\d+\s+[A-Z][^\n]{3,80})",
        r"(?:^|\n)\s*(Topic\s+\d+[:.\s]+[A-Z][^\n]{3,80})",
        r"(?:^|\n)\s*(Lesson\s+\d+[:.\s]+[A-Z][^\n]{3,80})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def chunk_text(text: str, source_type: str = "student_textbook") -> list[dict]:
    """Split text into curriculum-aligned chunks at natural boundaries.

    Strategy:
    1. Split on chapter/unit/section headers
    2. Split long sections by paragraphs
    3. Keep chunks between 300-1500 characters
    4. Track unit, topic, and page_number for each chunk
    """
    # No TOC skipping needed — the unit extraction rejects TOC entries
    # (they contain section refs like "1.1" which fail the clean name check)

    header_patterns = [
        r"(?=(?:^|\n)\s*(?:Chapter|Unit|Module)\s+\d+[\.\s:])",
        r"(?=(?:^|\n)\s*\d+\.\d+\s+[A-Z])",
        r"(?=(?:^|\n)\s*[A-Z][A-Z\s]{5,}(?:\n|$))",
        r"(?=(?:^|\n)\s*Lesson\s+\d+)",
        r"(?=(?:^|\n)\s*Topic\s+\d+)",
        r"(?=(?:^|\n)\s*Session\s+\d+)",
        r"(?=(?:^|\n)\s*Part\s+[A-Z0-9])",
        r"(?=(?:^|\n)\s*Section\s+\d+)",
    ]

    combined_pattern = "|".join(header_patterns)
    chunks = []

    if source_type == "teachers_guide" or source_type == "teacher_notes":
        paragraphs = re.split(r"\n\s*\n", text)
        current_chunk = ""
        current_unit = ""
        current_page = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            unit_match = re.search(r"Unit\s+(\d+):\s*([A-Z][^\n]{3,60})", para)
            if unit_match:
                name = unit_match.group(2).strip()
                if not re.search(r'\d+\.\d+', name) and not re.search(r'\b\d{2,}\b', name):
                    current_unit = f"Unit {unit_match.group(1)}: {name}"

            page_match = re.search(r"\[PAGE\s+(\d+)\]", para)
            if page_match:
                current_page = int(page_match.group(1))
            else:
                page_match = re.search(r"Grade\s+\d+\s+Biology\s+(\d+)", para)
                if page_match:
                    current_page = int(page_match.group(1))

            if len(current_chunk) + len(para) > 1500 and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "heading": _extract_heading(current_chunk),
                    "unit": current_unit,
                    "topic": _extract_topic(current_chunk),
                    "page_number": current_page,
                })
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "heading": _extract_heading(current_chunk),
                "unit": current_unit,
                "topic": _extract_topic(current_chunk),
                "page_number": current_page,
            })
    else:
        sections = re.split(combined_pattern, text)
        current_unit = ""
        current_page = 0

        for section in sections:
            section = section.strip()
            if not section or len(section) < 30:
                continue

            # Extract unit from this section's header
            unit_match = re.search(r"Unit\s+(\d+):\s*([A-Z][^\n]{3,60})", section)
            if unit_match:
                name = unit_match.group(2).strip()
                # Reject TOC entries: contain section refs, page numbers, or are followed by mostly whitespace/numbers
                if not re.search(r'\d+\.\d+', name) and not re.search(r'\b\d{2,}\b', name):
                    # Check if the section after the unit header has real content (not just TOC)
                    after_unit = section[unit_match.end():unit_match.end()+100].strip()
                    # TOC entries are followed by whitespace and page numbers, not paragraphs
                    if after_unit and not re.match(r'^[\s\d\t]+$', after_unit[:50]):
                        name = re.split(r'\s{2,}|\t', name)[0].strip()
                        if len(name) < 80:
                            current_unit = f"Unit {unit_match.group(1)}: {name}"

            # Extract page number from marker or text
            page_match = re.search(r"\[PAGE\s+(\d+)\]", section)
            if page_match:
                current_page = int(page_match.group(1))
            else:
                page_match = re.search(r"Grade\s+\d+\s+Biology\s+(\d+)", section)
                if page_match:
                    current_page = int(page_match.group(1))

            if len(section) > 2000:
                paragraphs = re.split(r"\n\s*\n", section)
                current = ""
                for para in paragraphs:
                    para = para.strip()
                    if not para:
                        continue

                    p_match = re.search(r"\[PAGE\s+(\d+)\]", para)
                    if p_match:
                        current_page = int(p_match.group(1))
                    else:
                        p_match = re.search(r"Grade\s+\d+\s+Biology\s+(\d+)", para)
                        if p_match:
                            current_page = int(p_match.group(1))

                    if len(current) + len(para) > 1200 and current:
                        chunks.append({
                            "text": current.strip(),
                            "heading": _extract_heading(current),
                            "unit": current_unit,
                            "topic": _extract_topic(current),
                            "page_number": current_page,
                        })
                        current = para
                    else:
                        current += "\n\n" + para if current else para
                if current:
                    chunks.append({
                        "text": current.strip(),
                        "heading": _extract_heading(current),
                        "unit": current_unit,
                        "topic": _extract_topic(current),
                        "page_number": current_page,
                    })
            else:
                section_unit = current_unit
                if not section_unit:
                    section_unit = _extract_unit(section)
                chunks.append({
                    "text": section,
                    "heading": _extract_heading(section),
                    "unit": section_unit,
                    "topic": _extract_topic(section),
                    "page_number": current_page,
                })

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


async def process_file(
    file_info: dict,
    embedder: Embedder,
    store: VectorStore,
    use_docling: bool = True,
) -> int:
    """Process a single curriculum file: extract, chunk, embed, store."""
    filepath = file_info["filepath"]
    grade = file_info["grade_level"]
    source_type = file_info["source_type"]
    filename = file_info["filename"]

    extractor = "Docling+OCR" if use_docling and filepath.endswith(".pdf") else "PyMuPDF"
    print(f"  Processing: Grade {grade}/{filename} ({source_type}) [{extractor}]")

    try:
        if filepath.endswith(".pdf"):
            pages = extract_text_from_pdf(filepath, use_docling=use_docling)
        elif filepath.endswith(".docx"):
            pages = extract_text_from_docx(filepath)
        elif filepath.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                pages = [{"text": f.read(), "page_number": 0}]
        else:
            return 0
    except Exception as e:
        print(f"    Extraction error: {e}")
        return 0

    if not pages or not any(p["text"] for p in pages):
        print(f"    No text extracted")
        return 0

    # Chunk per-page to preserve page numbers, then sub-chunk if needed
    all_chunks = []
    for p in pages:
        page_chunks = chunk_text(p["text"], source_type)
        for c in page_chunks:
            c["page_number"] = p["page_number"]
            all_chunks.append(c)
    chunks = all_chunks

    if not chunks:
        print(f"    No chunks created")
        return 0

    print(f"    Extracted {len(pages)} pages -> {len(chunks)} chunks")

    chunk_texts = [c["text"] for c in chunks]
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"g{grade}_{filename}_{i}"
        metadatas.append({
            "grade_level": grade,
            "source_type": source_type,
            "source_file": filename,
            "unit": chunk.get("unit", "") or "",
            "topic": chunk.get("topic", "") or "",
            "heading": chunk.get("heading", "") or chunk["text"][:80],
            "page_number": chunk.get("page_number", 0) or 0,
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
        print(f"    Stored {len(chunks)} chunks in ChromaDB")
        return len(chunks)
    except Exception as e:
        print(f"    Embedding/storage error: {e}")
        return 0


async def main():
    parser = argparse.ArgumentParser(description="Ingest curriculum materials into RAG vector store")
    parser.add_argument("--textbooks-dir", default=TEXTBOOKS_DIR, help="Path to textbooks directory")
    parser.add_argument("--clear", action="store_true", help="Clear all vectors before ingestion")
    parser.add_argument("--stats", action="store_true", help="Show store statistics")
    parser.add_argument("--query", type=str, help="Test retrieval with a query string")
    parser.add_argument("--grade", type=int, help="Filter query by grade level")
    parser.add_argument("--use-pymupdf", action="store_true", help="Use PyMuPDF instead of Docling+OCR")
    parser.add_argument("--ollama-embed", action="store_true", help="Use Ollama for embeddings instead of local model")

    args = parser.parse_args()

    if not os.path.isdir(args.textbooks_dir):
        print(f"Textbooks directory not found: {args.textbooks_dir}")
        print(f"   Create it and place PDFs in: {args.textbooks_dir}/Grade7/ ... Grade12/")
        sys.exit(1)

    embedder = Embedder()
    store = VectorStore()

    if args.clear:
        print("Clearing existing vectors...")
        await store.delete_collection()
        print("   Cleared.")

    if args.stats:
        count = store.count()
        print(f"Vector Store Statistics")
        print(f"   Collection: {settings.collection_name}")
        print(f"   Total chunks: {count}")
        print(f"   Persist path: {settings.vector_store_path}")
        return

    if args.query:
        from src.rag.retriever import Retriever
        print(f"Testing retrieval for: \"{args.query}\"")
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
        print(f"No supported files found in {args.textbooks_dir}")
        print(f"   Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
        print(f"   Expected structure:")
        print(f"     {args.textbooks_dir}/Grade7/biology_textbook.pdf")
        print(f"     {args.textbooks_dir}/Grade9/biology_teachers_guide.docx")
        sys.exit(0)

    use_docling = not args.use_pymupdf
    print(f"Found {len(files)} files to process (extractor: {'Docling+OCR' if use_docling else 'PyMuPDF'})\n")
    total_chunks = 0
    for f in files:
        chunks = await process_file(f, embedder, store, use_docling=use_docling)
        total_chunks += chunks

    count = store.count()
    print(f"\nIngestion complete!")
    print(f"   Files processed: {len(files)}")
    print(f"   Total chunks stored: {total_chunks}")
    print(f"   ChromaDB collection count: {count}")
    print(f"   Location: {settings.vector_store_path}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
