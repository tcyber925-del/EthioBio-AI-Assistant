"""
Migrate existing ChromaDB vectors to PostgreSQL pgvector.

Usage:
    DATABASE_URL=postgresql+asyncpg://... python scripts/migrate_to_pgvector.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.rag.vector_store import VectorStore


def _derive_topic_from_unit(unit_str: str) -> str:
    if ":" in unit_str:
        return unit_str.split(":", 1)[1].strip()
    return unit_str


async def main():
    chroma_store = VectorStore(use_pgvector=False)
    pg_store = VectorStore(use_pgvector=True)

    coll = chroma_store._get_collection()
    data = coll.get(include=["documents", "metadatas", "embeddings"])

    ids = data["ids"]
    documents = data["documents"]
    embeddings = data["embeddings"]
    metadatas = data["metadatas"]

    if not ids:
        print("No data in ChromaDB to migrate")
        return

    print(f"Found {len(ids)} chunks in ChromaDB")

    # Ensure topic is populated in metadata
    for meta in metadatas:
        if not meta.get("topic"):
            meta["topic"] = _derive_topic_from_unit(meta.get("unit", ""))

    batch_size = 100
    for i in range(0, len(ids), batch_size):
        batch_end = min(i + batch_size, len(ids))
        batch_ids = ids[i:batch_end]
        batch_docs = documents[i:batch_end]
        batch_embs = embeddings[i:batch_end]
        batch_metas = metadatas[i:batch_end]

        # Ensure all Python lists (Chromadb might return ndarray)
        batch_embs = [e.tolist() if hasattr(e, "tolist") else e for e in batch_embs]

        await pg_store.add_documents(batch_docs, batch_embs, batch_metas, batch_ids)
        print(f"  Migrated {batch_end}/{len(ids)} chunks", flush=True)

    count = await pg_store.count()
    print(f"\nMigration complete! PGVectorStore now has {count} chunks")
    print(f"ChromaDB still has {len(ids)} chunks (unchanged)")


if __name__ == "__main__":
    asyncio.run(main())
