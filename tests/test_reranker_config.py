from src.config import settings


class TestRerankerConfig:
    def test_reranker_disabled_returns_none_without_loading(self, monkeypatch):
        from src.retrieval import reranker

        monkeypatch.setattr(settings, "enable_reranker", False)
        monkeypatch.setattr(reranker, "_cross_encoder_model", None)
        called = []

        import sentence_transformers

        monkeypatch.setattr(sentence_transformers, "CrossEncoder", lambda name: called.append(name))

        assert reranker._get_or_create_cross_encoder() is None
        assert called == []

    def test_reranker_enabled_loads_model(self, monkeypatch):
        from src.retrieval import reranker

        monkeypatch.setattr(settings, "enable_reranker", True)
        monkeypatch.setattr(reranker, "_cross_encoder_model", None)

        import sentence_transformers

        fake = object()
        monkeypatch.setattr(sentence_transformers, "CrossEncoder", lambda name: fake)

        assert reranker._get_or_create_cross_encoder() is fake

    def test_reranker_default_enabled(self):
        assert settings.enable_reranker is True
