import pytest
from unittest.mock import AsyncMock, patch
from src.rag.embedder import Embedder
from src.rag.retriever import Retriever


@pytest.mark.asyncio
async def test_embedder_ollama_fallback(mock_router):
    embedder = Embedder(router=mock_router)
    result = await embedder.embed_text("What is photosynthesis?", use_ollama=True)
    assert isinstance(result, list)
    assert len(result) == 384
    assert all(isinstance(x, float) for x in result)


@pytest.mark.asyncio
async def test_retriever_retrieve(mock_router, mock_retriever):
    retriever = Retriever(
        embedder=Embedder(router=mock_router),
        vector_store=mock_retriever,
    )
    retriever.vector_store = AsyncMock()
    retriever.vector_store.query.return_value = {
        "documents": ["Test curriculum content"],
        "metadatas": [{"topic": "Cell Biology", "grade_level": 10}],
        "distances": [0.05],
        "ids": ["1"],
    }
    retriever.embedder = AsyncMock()
    retriever.embedder.embed_text.return_value = [0.1] * 384

    results = await retriever.retrieve("What is a cell?", grade_level=10, topic="Cell Biology")
    assert len(results) > 0
    assert "content" in results[0]
    assert "metadata" in results[0]


@pytest.mark.asyncio
async def test_format_context():
    retriever = Retriever()
    docs = [
        {"content": "Cell theory states...", "metadata": {"topic": "Cell Biology", "grade_level": 10}, "score": 0.95, "id": "1"},
        {"content": "Mitosis is...", "metadata": {"topic": "Cell Division", "grade_level": 11}, "score": 0.90, "id": "2"},
    ]
    context = retriever.format_context(docs)
    assert "[Source 1]" in context
    assert "[Source 2]" in context
    assert "Cell theory" in context
    assert "Mitosis" in context
