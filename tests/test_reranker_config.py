import sys
import types

from src.config import settings


class TestRerankerConfig:
    def test_reranker_disabled_returns_none_without_loading(self, monkeypatch):
        from src.retrieval import reranker

        monkeypatch.setattr(settings, "enable_reranker", False)
        monkeypatch.setattr(reranker, "_cross_encoder_model", None)
        called = []

        fake_st = types.ModuleType("sentence_transformers")
        fake_st.CrossEncoder = lambda name: called.append(name)
        monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

        assert reranker._get_or_create_cross_encoder() is None
        assert called == []

    def test_reranker_enabled_loads_model(self, monkeypatch):
        from src.retrieval import reranker

        monkeypatch.setattr(settings, "enable_reranker", True)
        monkeypatch.setattr(reranker, "_cross_encoder_model", None)

        fake_st = types.ModuleType("sentence_transformers")
        fake = object()
        fake_st.CrossEncoder = lambda name: fake
        monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

        assert reranker._get_or_create_cross_encoder() is fake

    def test_reranker_default_enabled(self):
        assert settings.enable_reranker is True
