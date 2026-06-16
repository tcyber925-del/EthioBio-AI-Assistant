"""
Embed Grade 10 OCR output: load JSON → chunk → embed → store → BM25 rebuild.
Uses Ollama batch API (/api/embed) for fast 768-dim embeddings.
"""
import asyncio, httpx, json, os, sys, time

sys.path.insert(0, "/app")
os.environ["PYTHONUNBUFFERED"] = "1"

import scripts.ingest_curriculum as ic
from src.config import settings

OCR_JSON = "/tmp/grade10_ocr.json"
GRADE = 10
FILENAME = "grade 10-biology_kehulumcom_d02c.pdf"
SOURCE_TYPE = "student_textbook"
OLLAMA_URL = "http://ollama:11434"
EMBED_MODEL = "nomic-embed-text"
BATCH_SIZE = 32
EMBED_DIM = 768

async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using Ollama batch API."""
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as c:
            try:
                r = await c.post(f"{OLLAMA_URL}/api/embed", json={
                    "model": EMBED_MODEL,
                    "input": batch,
                })
                r.raise_for_status()
                result = r.json()
                for emb in result["embeddings"]:
                    all_embeddings.append(emb)
            except Exception as e:
                print(f"  Batch {i//BATCH_SIZE} error: {e}, using zeros", flush=True)
                for _ in batch:
                    all_embeddings.append([0.0] * EMBED_DIM)
        if (i // BATCH_SIZE + 1) % 5 == 0 or i + BATCH_SIZE >= len(texts):
            print(f"  Embedded {min(i+BATCH_SIZE, len(texts))}/{len(texts)}...", flush=True)
    return all_embeddings

async def main():
    print(f"Loading OCR output from {OCR_JSON}...")
    with open(OCR_JSON) as f:
        data = json.load(f)
    print(f"  {len(data['ocr_pages'])} pages with text (from {data['total_pages']} total)")

    store = ic.VectorStore()

    # Delete and recreate collection at 768-dim
    print("Recreating ChromaDB collection at 768-dim...")
    try:
        coll = store._get_collection()
        await store.delete_collection()
        print("  Old collection deleted.")
    except Exception as e:
        print(f"  Collection delete: {e}")
    store = ic.VectorStore()  # fresh instance
    print("  New collection created.")

    # Process: chunk per page, filter, embed, store
    all_chunks = []
    for p in data["ocr_pages"]:
        cleaned = ic._strip_control_chars(p["text"])
        page_chunks = ic.chunk_text(cleaned, SOURCE_TYPE)
        for c in page_chunks:
            c["page_number"] = p["page_number"]
            all_chunks.append(c)
    chunks = all_chunks

    if not chunks:
        print("No chunks created!")
        return

    before = len(chunks)
    filtered = []
    for c in chunks:
        text = c["text"]
        if len(text) < 80:
            continue
        if ic._is_garbled(text, alpha_threshold=0.50):
            continue
        if ic._contains_control_chars(text):
            continue
        filtered.append(c)
    chunks = filtered
    if before != len(chunks):
        print(f"  Filtered out {before - len(chunks)} garbled chunks")

    if not chunks:
        print("All chunks garbled!")
        return

    print(f"  {len(chunks)} quality chunks (from {len(data['ocr_pages'])} OCR pages)")

    for chunk in chunks:
        if not chunk.get("unit"):
            chunk["unit"] = ic._extract_unit(chunk["text"])
        if not chunk.get("heading"):
            chunk["heading"] = ic._extract_heading(chunk["text"])

    chunk_texts = [c["text"] for c in chunks]
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"g{GRADE}_{FILENAME}_{i}"
        metadatas.append({
            "grade_level": GRADE,
            "source_type": SOURCE_TYPE,
            "source_file": FILENAME,
            "unit": chunk.get("unit", "") or "",
            "section": chunk.get("section", "") or "",
            "subtopic": chunk.get("subtopic", "") or "",
            "topic": chunk.get("topic", "") or "",
            "heading": chunk.get("heading", "") or chunk["text"][:80],
            "page_number": chunk.get("page_number", 0) or 0,
            "chunk_index": i,
        })
        ids.append(chunk_id)

    print(f"Embedding {len(chunks)} chunks...")
    t0 = time.time()
    embeddings = await embed_batch(chunk_texts)
    print(f"  Embeddings done ({time.time()-t0:.1f}s)")

    print("Storing in ChromaDB...")
    await store.add_documents(
        texts=chunk_texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )
    print(f"  Stored {len(chunks)} chunks in ChromaDB")

    print("Rebuilding BM25 index...")
    from src.retrieval.adapter import VectorStoreAdapter
    adapter = VectorStoreAdapter(vector_store=store)
    adapter.build_bm25_index()

    count = store.count()
    print(f"\nDone! {len(chunks)} chunks stored, total ChromaDB: {count}")

if __name__ == "__main__":
    asyncio.run(main())
