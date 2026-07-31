"""Regression tests for lazy BM25 index building inside a running event loop.

The old implementation used `loop.run_until_complete()` from a sync helper,
which raises `RuntimeError: this event loop is already running` under
uvloop (FastAPI). The fix awaits the async `build_bm25_index()` instead.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.retrieval.bm25 import BM25Index


@pytest.fixture
def tmp_index(tmp_path) -> BM25Index:
    return BM25Index(persist_path=str(tmp_path / "bm25.pkl"))


class _StubReranker:
    def rerank(self, query, passages, top_k=3, content_key="content"):
        return passages[:top_k]


def _make_adapter(vector_store: MagicMock, tmp_index: BM25Index):
    from src.retrieval.adapter import VectorStoreAdapter

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.0] * 384
    return VectorStoreAdapter(
        embedder=embedder,
        vector_store=vector_store,
        bm25_index=tmp_index,
        reranker=_StubReranker(),
    )


class TestLazyBm25Build:
    async def test_pgvector_build_awaits_get_all_in_running_loop(self, tmp_index):
        pg = AsyncMock()
        pg.get_all.return_value = {
            "documents": [
                "cells are the basic unit of life",
                "dna carries genetic information",
            ],
            "metadatas": [{"grade_level": 10}, {"grade_level": 10}],
            "ids": ["1", "2"],
        }
        vector_store = MagicMock()
        vector_store._use_pgvector = True
        vector_store._get_pg.return_value = pg

        adapter = _make_adapter(vector_store, tmp_index)
        results = await adapter._bm25_search_raw("dna", n_results=5)

        assert results, "BM25 search should return results after lazy build"
        assert tmp_index.exists()
        pg.get_all.assert_awaited_once()

    async def test_chroma_build_awaits_collection_get_in_running_loop(self, tmp_index):
        collection = MagicMock()
        collection.count.return_value = 0
        collection.get.return_value = {
            "documents": ["mitochondria produce energy"],
            "metadatas": [{"grade_level": 11}],
            "ids": ["c1"],
        }
        vector_store = MagicMock()
        vector_store._use_pgvector = False
        vector_store._get_collection.return_value = collection

        adapter = _make_adapter(vector_store, tmp_index)
        results = await adapter._bm25_search_raw("mitochondria", n_results=5)

        assert results, "BM25 search should return results after lazy build"
        assert tmp_index.exists()
        collection.get.assert_called_once()

    async def test_build_failure_degrades_to_empty(self, tmp_index):
        vector_store = MagicMock()
        vector_store._use_pgvector = True

        adapter = _make_adapter(vector_store, tmp_index)
        adapter.build_bm25_index = AsyncMock(side_effect=RuntimeError("boom"))

        results = await adapter._bm25_search_raw("dna", n_results=5)

        assert results == []
        assert not tmp_index.exists()

    async def test_skips_rebuild_when_index_exists(self, tmp_index):
        vector_store = MagicMock()
        vector_store._use_pgvector = True
        vector_store._get_pg.return_value = AsyncMock()

        adapter = _make_adapter(vector_store, tmp_index)
        adapter.build_bm25_index = AsyncMock()
        tmp_index.build(
            documents=["already built"],
            ids=["0"],
            metadatas=[{}],
        )

        await adapter._bm25_search_raw("dna", n_results=5)

        adapter.build_bm25_index.assert_not_awaited()


class TestHybridSearchAwait:
    async def test_hybrid_search_builds_bm25_in_running_loop(self, tmp_index):
        pg = AsyncMock()
        pg.get_all.return_value = {
            "documents": [
                "cells are the basic unit of life",
                "dna carries genetic information",
            ],
            "metadatas": [{"grade_level": 10}, {"grade_level": 10}],
            "ids": ["1", "2"],
        }
        vector_store = MagicMock()
        vector_store._use_pgvector = True
        vector_store._get_pg.return_value = pg
        vector_store.query = AsyncMock(
            return_value={"documents": [], "metadatas": [], "distances": [], "ids": []}
        )

        adapter = _make_adapter(vector_store, tmp_index)
        results = await adapter.search("dna", n_results=2)

        assert tmp_index.exists()
        pg.get_all.assert_awaited_once()
        assert len(results) >= 1
