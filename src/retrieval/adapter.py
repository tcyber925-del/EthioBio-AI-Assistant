"""
VectorStoreAdapter — hybrid search over ChromaDB (dense) + BM25 (sparse) + reranking.

All retrieval-adjacent code goes through this interface.
ChromaDB can be swapped without touching agents or ingestion.
"""

from typing import Optional

import structlog

from src.rag.embedder import Embedder
from src.rag.vector_store import VectorStore
from src.retrieval.bm25 import BM25Index
from src.retrieval.reranker import Reranker

logger = structlog.get_logger()


class RetrievalResult:
    def __init__(self, content: str, metadata: dict, score: float, source_id: str):
        self.content = content
        self.metadata = metadata
        self.score = score
        self.source_id = source_id


class RetrievalFilter:
    def __init__(
        self,
        grade_level: Optional[int] = None,
        topic: Optional[str] = None,
        unit: Optional[str] = None,
        source_type: Optional[str] = None,
        language: str = "en",
    ):
        self.grade_level = grade_level
        self.topic = topic
        self.unit = unit
        self.source_type = source_type
        self.language = language

    def to_chroma_where(self) -> Optional[dict]:
        filters = []
        if self.grade_level:
            filters.append({"grade_level": {"$eq": self.grade_level}})
        if self.topic:
            filters.append({"topic": {"$eq": self.topic}})
        if self.unit:
            filters.append({"unit": {"$eq": self.unit}})
        if self.source_type:
            filters.append({"source_type": {"$eq": self.source_type}})
        if self.language and self.language != "en":
            filters.append({"language": {"$eq": self.language}})

        if not filters:
            return None
        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}


class VectorStoreAdapter:
    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        vector_store: Optional[VectorStore] = None,
        bm25_index: Optional[BM25Index] = None,
        reranker: Optional[Reranker] = None,
        use_hybrid: bool = True,
        dense_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ):
        self.vector_store = vector_store or VectorStore()
        store_dim = self._detect_store_dimension()
        local_dim = 384

        if embedder:
            self.embedder = embedder
        elif store_dim and store_dim != local_dim:
            logger.info("embedder_forcing_ollama", store_dim=store_dim, local_dim=local_dim)
            self.embedder = Embedder(force_ollama=True)
        else:
            self.embedder = Embedder()

        self.bm25_index = bm25_index or BM25Index()
        self.reranker = reranker or Reranker()
        self.use_hybrid = use_hybrid
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight

    def _detect_store_dimension(self) -> Optional[int]:
        """Detect embedding dimension from the vector store."""
        try:
            collection = self.vector_store._get_collection()
            count = collection.count()
            if count == 0:
                return None
            sample = collection.get(include=["embeddings"], limit=1)
            if sample["embeddings"]:
                return len(sample["embeddings"][0])
        except Exception as e:
            logger.warning("store_dimension_detect_failed", error=str(e))
        return None

    async def search(
        self,
        query: str,
        n_results: int = 3,
        filter_obj: Optional[RetrievalFilter] = None,
    ) -> list[RetrievalResult]:
        if self.use_hybrid:
            return await self._hybrid_search(query, n_results, filter_obj)
        return await self._dense_search(query, n_results, filter_obj)

    async def _hybrid_search(
        self,
        query: str,
        n_results: int,
        filter_obj: Optional[RetrievalFilter],
    ) -> list[RetrievalResult]:
        """Hybrid: dense (ChromaDB) + sparse (BM25) → merge → rerank → top-k."""
        grade_level = filter_obj.grade_level if filter_obj else None
        source_type = filter_obj.source_type if filter_obj else None

        fetch_k = max(n_results * 2, 10)

        dense_results = await self._dense_search_raw(query, fetch_k, filter_obj)
        bm25_results = self._bm25_search_raw(query, fetch_k, grade_level, source_type)

        merged = self._merge_results(dense_results, bm25_results)

        reranked = self.reranker.rerank(query, merged, top_k=n_results)

        return [
            RetrievalResult(
                content=r["content"],
                metadata=r.get("metadata", {}),
                score=r.get("score", 0.0),
                source_id=r.get("doc_id", r.get("source_id", "")),
            )
            for r in reranked
        ]

    async def _dense_search(
        self,
        query: str,
        n_results: int,
        filter_obj: Optional[RetrievalFilter],
    ) -> list[RetrievalResult]:
        """Pure dense search (original behavior)."""
        query_embedding = await self.embedder.embed_text(query)
        where = filter_obj.to_chroma_where() if filter_obj else None

        results = await self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )

        retrieved = []
        for i in range(len(results["documents"])):
            retrieved.append(
                RetrievalResult(
                    content=results["documents"][i],
                    metadata=results["metadatas"][i] if i < len(results["metadatas"]) else {},
                    score=1.0 - results["distances"][i] if i < len(results["distances"]) else 0.0,
                    source_id=results["ids"][i] if i < len(results["ids"]) else "",
                )
            )

        logger.info("adapter_search_dense", query_preview=query[:50], results=len(retrieved))
        return retrieved

    async def _dense_search_raw(
        self,
        query: str,
        n_results: int,
        filter_obj: Optional[RetrievalFilter],
    ) -> list[dict]:
        """Dense search returning raw dicts for merging."""
        query_embedding = await self.embedder.embed_text(query)
        where = filter_obj.to_chroma_where() if filter_obj else None

        results = await self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
        )

        retrieved = []
        for i in range(len(results["documents"])):
            retrieved.append(
                {
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i] if i < len(results["metadatas"]) else {},
                    "dense_score": (
                        1.0 - results["distances"][i] if i < len(results["distances"]) else 0.0
                    ),
                    "doc_id": results["ids"][i] if i < len(results["ids"]) else "",
                }
            )
        return retrieved

    def _bm25_search_raw(
        self,
        query: str,
        n_results: int,
        grade_level: Optional[int] = None,
        source_type: Optional[str] = None,
    ) -> list[dict]:
        """BM25 search returning raw dicts for merging."""
        if not self.bm25_index.exists():
            return []

        bm25_results = self.bm25_index.search(
            query,
            n_results=n_results,
            grade_level=grade_level,
            source_type=source_type,
        )

        retrieved = []
        for r in bm25_results:
            doc_text = self.bm25_index.get_document_text(r["index"])
            retrieved.append(
                {
                    "content": doc_text,
                    "metadata": r.get("metadata", {}),
                    "bm25_score": r["score"],
                    "doc_id": r["doc_id"],
                }
            )
        return retrieved

    def _merge_results(
        self,
        dense_results: list[dict],
        bm25_results: list[dict],
    ) -> list[dict]:
        """Merge dense and BM25 results using reciprocal rank fusion + weighted score."""
        doc_map: dict[str, dict] = {}

        for r in dense_results:
            doc_id = r["doc_id"]
            doc_map[doc_id] = {
                "content": r["content"],
                "metadata": r["metadata"],
                "doc_id": doc_id,
                "dense_score": r.get("dense_score", 0.0),
                "bm25_score": 0.0,
            }

        for r in bm25_results:
            doc_id = r["doc_id"]
            if doc_id in doc_map:
                doc_map[doc_id]["bm25_score"] = r.get("bm25_score", 0.0)
            else:
                doc_map[doc_id] = {
                    "content": r["content"],
                    "metadata": r["metadata"],
                    "doc_id": doc_id,
                    "dense_score": 0.0,
                    "bm25_score": r.get("bm25_score", 0.0),
                }

        for doc_id, doc in doc_map.items():
            doc["score"] = (
                self.dense_weight * doc["dense_score"] + self.bm25_weight * doc["bm25_score"]
            )

        merged = sorted(doc_map.values(), key=lambda x: x["score"], reverse=True)
        return merged

    def format_context(self, results: list[RetrievalResult], max_chars: int = 4000) -> str:
        sections = []
        char_count = 0
        for i, r in enumerate(results, 1):
            grade = r.metadata.get("grade_level", "")
            unit = r.metadata.get("unit", "")
            section = r.metadata.get("section", "")
            subtopic = r.metadata.get("subtopic", "")
            topic = r.metadata.get("topic", "")
            page = r.metadata.get("page_number", 0)
            source_type = r.metadata.get("source_type", "")

            header = f"[Source {i}]"
            if grade:
                header += f" Grade {grade} Biology"
            if unit:
                header += f" | {unit}"
            if section:
                header += f" | {section}"
            if subtopic:
                header += f" | {subtopic}"
            if topic:
                header += f" | {topic}"
            if page:
                header += f" | p.{page}"
            if source_type:
                header += f" ({source_type})"

            entry = f"{header}\n{r.content}"
            if char_count + len(entry) > max_chars:
                remaining = max_chars - char_count
                if remaining > 200:
                    sections.append(f"{header}\n{r.content[:remaining]}...")
                break

            sections.append(entry)
            char_count += len(entry)

        citation_instruction = (
            "IMPORTANT: When answering, cite the source for each key point "
            "using this exact format:\n"
            "(Grade X, Unit Y: Title, Section N.N: Name, p. Z)\n"
            "Example: (Grade 10, Unit 3: Biochemical Molecules, "
            "Section 3.1: Carbohydrates, p. 77)\n\n"
        )

        return citation_instruction + "\n\n".join(sections)

    def count(self) -> int:
        return self.vector_store.count()

    def build_bm25_index(self):
        """Build BM25 index from all documents in the vector store."""
        collection = self.vector_store._get_collection()
        all_docs = collection.get(include=["documents", "metadatas"])

        if not all_docs["documents"]:
            logger.warning("bm25_build_no_documents")
            return

        self.bm25_index.clear()
        self.bm25_index.build(
            documents=all_docs["documents"],
            ids=all_docs["ids"],
            metadatas=all_docs["metadatas"],
        )
        logger.info("bm25_built_from_store", count=len(all_docs["documents"]))
