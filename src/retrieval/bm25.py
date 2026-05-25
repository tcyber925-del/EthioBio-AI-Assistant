"""BM25 sparse retrieval module for hybrid search.

Maintains a parallel BM25 index over the same text chunks stored in ChromaDB.
Persisted to disk via pickle for fast reload.
"""

import os
import pickle
import re
from typing import Optional

import structlog
from rank_bm25 import BM25Okapi

logger = structlog.get_logger()

DEFAULT_INDEX_PATH = "./data/vectors/bm25_index.pkl"


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: lowercase, split on non-alphanumeric, remove short tokens."""
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)
    return [t for t in tokens if len(t) > 1]


class BM25Index:
    """Wraps rank-bm25 with persistence and metadata tracking."""

    def __init__(self, persist_path: str = DEFAULT_INDEX_PATH):
        self.persist_path = persist_path
        self._bm25: Optional[BM25Okapi] = None
        self._corpus: list[list[str]] = []
        self._doc_ids: list[str] = []
        self._metadatas: list[dict] = []

    def build(
        self,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict],
    ):
        """Build BM25 index from raw documents."""
        self._corpus = [_tokenize(doc) for doc in documents]
        self._doc_ids = ids
        self._metadatas = metadatas
        self._bm25 = BM25Okapi(self._corpus)
        self._save()
        logger.info("bm25_index_built", num_docs=len(documents))

    def search(
        self,
        query: str,
        n_results: int = 20,
        grade_level: Optional[int] = None,
        source_type: Optional[str] = None,
    ) -> list[dict]:
        """Search BM25 index, optionally filtered by metadata.

        Returns list of {doc_id, content, score, metadata}.
        """
        if self._bm25 is None:
            self._load()
            if self._bm25 is None:
                return []

        query_tokens = _tokenize(query)
        scores = self._bm25.get_scores(query_tokens)

        candidates = []
        for i, score in enumerate(scores):
            meta = self._metadatas[i] if i < len(self._metadatas) else {}
            if grade_level and meta.get("grade_level") != grade_level:
                continue
            if source_type and meta.get("source_type") != source_type:
                continue
            candidates.append({
                "doc_id": self._doc_ids[i],
                "score": float(score),
                "metadata": meta,
                "index": i,
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:n_results]

    def get_documents(self, indices: list[int]) -> list[str]:
        """Retrieve original document texts by corpus index."""
        if self._bm25 is None:
            self._load()
        result = []
        for idx in indices:
            if idx < len(self._corpus):
                result.append(" ".join(self._corpus[idx]))
        return result

    def get_document_text(self, index: int) -> str:
        """Get the original text for a corpus index."""
        if self._bm25 is None:
            self._load()
        if index < len(self._corpus):
            return " ".join(self._corpus[index])
        return ""

    @property
    def doc_ids(self) -> list[str]:
        return self._doc_ids

    @property
    def metadatas(self) -> list[dict]:
        return self._metadatas

    @property
    def corpus(self) -> list[list[str]]:
        return self._corpus

    def _save(self):
        os.makedirs(os.path.dirname(self.persist_path) or ".", exist_ok=True)
        with open(self.persist_path, "wb") as f:
            pickle.dump({
                "corpus": self._corpus,
                "doc_ids": self._doc_ids,
                "metadatas": self._metadatas,
            }, f)

    def _load(self):
        if not os.path.exists(self.persist_path):
            logger.warning("bm25_index_not_found", path=self.persist_path)
            return
        with open(self.persist_path, "rb") as f:
            data = pickle.load(f)
        self._corpus = data["corpus"]
        self._doc_ids = data["doc_ids"]
        self._metadatas = data["metadatas"]
        self._bm25 = BM25Okapi(self._corpus)
        logger.info("bm25_index_loaded", num_docs=len(self._corpus))

    def exists(self) -> bool:
        return os.path.exists(self.persist_path)

    def clear(self):
        if os.path.exists(self.persist_path):
            os.remove(self.persist_path)
        self._bm25 = None
        self._corpus = []
        self._doc_ids = []
        self._metadatas = []
        logger.info("bm25_index_cleared")
