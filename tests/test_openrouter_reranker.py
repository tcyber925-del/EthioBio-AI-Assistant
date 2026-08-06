import json

import httpx
import pytest

from src.core.retrieval.openrouter_reranker import OpenRouterReranker, RerankerError


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self._responses.pop(0)


def _json_response(payload):
    return httpx.Response(200, json=payload)


def _install_fake_client(monkeypatch, responses):
    def fake_client(*a, **k):
        return _FakeClient(responses)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)


async def test_rerank_returns_scores_in_index_order(monkeypatch):
    _install_fake_client(
        monkeypatch,
        [
            _json_response(
                {
                    "results": [
                        {"index": 1, "relevance_score": 0.9},
                        {"index": 0, "relevance_score": 0.5},
                    ]
                }
            )
        ],
    )
    out = await OpenRouterReranker().rerank("query", ["doc_a", "doc_b"])
    assert out == pytest.approx([0.5, 0.9])


async def test_rerank_batches_documents(monkeypatch):
    _install_fake_client(
        monkeypatch,
        [
            _json_response({"results": [{"index": i, "relevance_score": 0.1} for i in range(64)]}),
            _json_response({"results": [{"index": i, "relevance_score": 0.2} for i in range(64)]}),
            _json_response({"results": [{"index": 0, "relevance_score": 0.3}]}),
        ],
    )
    monkeypatch.setattr("src.config.settings.reranker_batch_size", 64)
    out = await OpenRouterReranker().rerank("query", ["d"] * 129)
    assert len(out) == 129
    assert out[0] == pytest.approx(0.1)
    assert out[64] == pytest.approx(0.2)
    assert out[128] == pytest.approx(0.3)


async def test_rerank_raises_on_api_error(monkeypatch):
    _install_fake_client(monkeypatch, [httpx.Response(500, json={})])
    with pytest.raises(RerankerError):
        await OpenRouterReranker().rerank("q", ["a"])


async def test_rerank_raises_on_timeout(monkeypatch):
    def boom(*a, **k):
        raise httpx.TimeoutException("timed out")

    class _BoomClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kwargs):
            boom()

    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _BoomClient())
    with pytest.raises(RerankerError):
        await OpenRouterReranker().rerank("q", ["a"])


async def test_rerank_empty_documents_returns_empty():
    assert await OpenRouterReranker().rerank("q", []) == []


async def test_missing_index_fills_zero(monkeypatch):
    _install_fake_client(
        monkeypatch, [_json_response({"results": [{"index": 0, "relevance_score": 0.9}]})]
    )
    out = await OpenRouterReranker().rerank("q", ["a", "b"])
    assert out == pytest.approx([0.9, 0.0])
