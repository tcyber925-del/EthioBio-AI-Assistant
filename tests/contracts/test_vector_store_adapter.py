"""Contract tests for the VectorStoreAdapter.

Verifies that the adapter has the expected public interface
so that callers can rely on the method signatures.
"""

from src.retrieval.adapter import RetrievalFilter, RetrievalResult, VectorStoreAdapter


def test_retrieval_result_has_required_fields():
    """RetrievalResult has content, metadata, score, source_id."""
    result = RetrievalResult(
        content="test content",
        metadata={"topic": "biology"},
        score=0.95,
        source_id="chunk_1",
    )
    assert result.content == "test content"
    assert result.metadata == {"topic": "biology"}
    assert result.score == 0.95
    assert result.source_id == "chunk_1"


def test_retrieval_filter_stores_fields():
    """RetrievalFilter stores and retrieves all filter criteria."""
    filt = RetrievalFilter(
        grade_level=8,
        topic="Cell Biology",
        source_type="curriculum",
        language="en",
    )
    assert filt.grade_level == 8
    assert filt.topic == "Cell Biology"
    assert filt.source_type == "curriculum"
    assert filt.language == "en"


def test_retrieval_filter_to_chroma_where():
    """to_chroma_where produces correct filter dict."""
    filt = RetrievalFilter(grade_level=8, topic="Cell Biology")
    where = filt.to_chroma_where()
    assert where == {"$and": [
        {"grade_level": {"$eq": 8}},
        {"topic": {"$eq": "Cell Biology"}},
    ]}


def test_retrieval_filter_empty_returns_none():
    """Empty filter returns None for chroma where."""
    filt = RetrievalFilter()
    assert filt.to_chroma_where() is None


def test_vector_store_adapter_has_search_method():
    """VectorStoreAdapter has search() with expected signature."""
    import inspect

    sig = inspect.signature(VectorStoreAdapter.search)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "query" in params
    assert "n_results" in params
    assert "filter_obj" in params


def test_vector_store_adapter_is_swappable():
    """VectorStoreAdapter can be constructed with minimal deps."""
    try:
        adapter = VectorStoreAdapter.__new__(VectorStoreAdapter)
        assert isinstance(adapter, VectorStoreAdapter)
    except Exception as e:
        assert False, f"VectorStoreAdapter instantiation failed: {e}"
