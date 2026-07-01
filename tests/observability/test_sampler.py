
from src.observability.evaluation.sampler import EvalSampler


class TestEvalSampler:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.setattr("src.config.settings.eval_enabled", False)
        monkeypatch.setattr("src.config.settings.eval_sampling_rate", 0.5)
        s = EvalSampler()
        assert not s.should_evaluate()

    def test_always_sample_on_error(self, monkeypatch):
        monkeypatch.setattr("src.config.settings.eval_enabled", True)
        monkeypatch.setattr("src.config.settings.eval_sampling_rate", 0.0)
        s = EvalSampler()
        assert s.should_evaluate(is_error=True)

    def test_always_sample_on_large_response(self, monkeypatch):
        monkeypatch.setattr("src.config.settings.eval_enabled", True)
        monkeypatch.setattr("src.config.settings.eval_sampling_rate", 0.0)
        s = EvalSampler()
        assert s.should_evaluate(token_count=5000)

    def test_random_sampling(self, monkeypatch):
        monkeypatch.setattr("src.config.settings.eval_enabled", True)
        monkeypatch.setattr("src.config.settings.eval_sampling_rate", 1.0)
        s = EvalSampler()
        assert s.should_evaluate()

    def test_random_sampling_never(self, monkeypatch):
        monkeypatch.setattr("src.config.settings.eval_enabled", True)
        monkeypatch.setattr("src.config.settings.eval_sampling_rate", 0.0)
        s = EvalSampler()
        assert not s.should_evaluate()
