"""
Re-ingest all grades using local sentence-transformers (384-dim, batched).
Grade 10 uses OCR JSON, others use PyMuPDF extraction.
"""
import asyncio, json, os, sys, time

sys.path.insert(0, "/app")
os.environ["PYTHONUNBUFFERED"] = "1"

import scripts.ingest_curriculum as ic
from src.config import settings

OCR_JSON = "/tmp/grade10_ocr.json"
GRADE10_FILE = "grade 10-biology_kehulumcom_d02c.pdf"

async def main():
    store = ic.VectorStore()
    embedder = ic.Embedder()

    # Recreate collection at 384-dim
    print("Recreating ChromaDB collection at 384-dim...")
    try:
        await store.delete_collection()
        print("  Deleted old collection.")
    except Exception as e:
        print(f"  Delete: {e}")
    store = ic.VectorStore()
    print("  Fresh collection ready.\n")

    # Process grades 9, 11, 12 via PyMuPDF
    files = ic.scan_files(ic.TEXTBOOKS_DIR)
    for f in files:
        g = f["grade_level"]
        if g == 10:
            continue
        filepath = f["filepath"]
        filename = f["filename"]
        source_type = f["source_type"]
        print(f"Grade {g}: {filename} [{source_type}]")
        pages = ic._extract_with_pymupdf(filepath)
        if not pages:
            print(f"  No pages extracted!")
            continue

        all_chunks = []
        for p in pages:
            cleaned = ic._strip_control_chars(p["text"])
            page_chunks = ic.chunk_text(cleaned, source_type)
            for c in page_chunks:
                c["page_number"] = p["page_number"]
                all_chunks.append(c)

        chunks = [c for c in all_chunks if len(c["text"]) >= 80
                  and not ic._is_garbled(c["text"], 0.50)
                  and not ic._contains_control_chars(c["text"])]
        if not chunks:
            print(f"  Grade {g}: no valid chunks!")
            continue

        for c in chunks:
            if not c.get("unit"): c["unit"] = ic._extract_unit(c["text"])
            if not c.get("heading"): c["heading"] = ic._extract_heading(c["text"])

        texts = [c["text"] for c in chunks]
        metadatas = [{
            "grade_level": g, "source_type": source_type,
            "source_file": filename, "unit": c.get("unit","") or "",
            "section": c.get("section","") or "", "subtopic": c.get("subtopic","") or "",
            "topic": c.get("topic","") or "",
            "heading": c.get("heading","") or c["text"][:80],
            "page_number": c.get("page_number",0) or 0, "chunk_index": i,
        } for i, c in enumerate(chunks)]
        ids = [f"g{g}_{filename}_{i}" for i in range(len(chunks))]

        print(f"  Embedding {len(chunks)} chunks...", flush=True)
        t0 = time.time()
        embeddings = await embedder.embed_batch(texts)
        print(f"  Embeddings: {time.time()-t0:.1f}s", flush=True)

        await store.add_documents(texts=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
        print(f"  Stored {len(chunks)} chunks\n")

    # Process grade 10 from OCR JSON
    print(f"Grade 10: {GRADE10_FILE} [OCR]")
    with open(OCR_JSON) as f:
        data = json.load(f)
    print(f"  {len(data['ocr_pages'])} OCR pages")

    all_chunks = []
    for p in data["ocr_pages"]:
        cleaned = ic._strip_control_chars(p["text"])
        page_chunks = ic.chunk_text(cleaned, "student_textbook")
        for c in page_chunks:
            c["page_number"] = p["page_number"]
            all_chunks.append(c)

    chunks = [c for c in all_chunks if len(c["text"]) >= 80
              and not ic._is_garbled(c["text"], 0.50)
              and not ic._contains_control_chars(c["text"])]
    if not chunks:
        print("  No valid chunks!")
    else:
        for c in chunks:
            if not c.get("unit"): c["unit"] = ic._extract_unit(c["text"])
            if not c.get("heading"): c["heading"] = ic._extract_heading(c["text"])

        texts = [c["text"] for c in chunks]
        metadatas = [{
            "grade_level": 10, "source_type": "student_textbook",
            "source_file": GRADE10_FILE, "unit": c.get("unit","") or "",
            "section": c.get("section","") or "", "subtopic": c.get("subtopic","") or "",
            "topic": c.get("topic","") or "",
            "heading": c.get("heading","") or c["text"][:80],
            "page_number": c.get("page_number",0) or 0, "chunk_index": i,
        } for i, c in enumerate(chunks)]
        ids = [f"g10_{GRADE10_FILE}_{i}" for i in range(len(chunks))]

        print(f"  Embedding {len(chunks)} chunks...", flush=True)
        t0 = time.time()
        embeddings = await embedder.embed_batch(texts)
        print(f"  Embeddings: {time.time()-t0:.1f}s", flush=True)

        await store.add_documents(texts=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
        print(f"  Stored {len(chunks)} chunks")

    # BM25 rebuild
    print("\nRebuilding BM25 index...")
    from src.retrieval.adapter import VectorStoreAdapter
    adapter = VectorStoreAdapter(vector_store=store)
    adapter.build_bm25_index()

    total = store.count()
    print(f"\nDone! Total chunks: {total}")

if __name__ == "__main__":
    asyncio.run(main())
