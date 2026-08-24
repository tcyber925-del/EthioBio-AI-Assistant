import uuid
from types import SimpleNamespace

from src.evaluation.langsmith.evaluators import (
    llm_judge_evaluator,
    topic_coverage_evaluator,
)
from src.evaluation.langsmith.sync_datasets import _examples_for, _stable_id
from src.llm.router import _llm_inputs, _llm_outputs
from src.observability.langsmith import capture_run_id, should_trace, traced_run


class TestLangSmithTracing:
    def test_traced_run_yields_without_tracing(self):
        # tracing_context is None when langsmith is absent/disabled
        with traced_run(enabled=True) as ctx:
            assert ctx is None

    def test_traced_run_respects_enabled_flag(self, monkeypatch):
        called = []

        class FakeContext:
            def __init__(self, **kw):
                called.append(kw)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        monkeypatch.setattr("src.observability.langsmith.tracing_context", FakeContext)
        with traced_run(enabled=True, metadata={"k": "v"}):
            pass
        assert len(called) == 1
        assert called[0]["enabled"] is True
        assert called[0]["metadata"] == {"k": "v"}

        with traced_run(enabled=False):
            pass
        assert len(called) == 1  # not called again

    def test_should_trace_force_overrides_sampling(self, monkeypatch):
        monkeypatch.setattr("src.config.settings.langsmith_tracing_enabled", True)
        monkeypatch.setattr("src.config.settings.langsmith_api_key", "lsv1_x")
        monkeypatch.setattr("src.config.settings.langsmith_sampling_rate", 0.0)
        assert not should_trace()
        assert should_trace(force=True)

    def test_should_trace_disabled(self, monkeypatch):
        monkeypatch.setattr("src.config.settings.langsmith_tracing_enabled", False)
        monkeypatch.setattr("src.config.settings.langsmith_api_key", "lsv1_x")
        assert not should_trace(force=True)


class TestCaptureRunId:
    def test_returns_string_not_uuid_object(self, monkeypatch):
        # RunTree.id is a uuid.UUID; persisting it into a JSON column crashes
        # save_trace with "Object of type UUID is not JSON serializable".
        run_uuid = uuid.uuid4()
        monkeypatch.setattr(
            "src.observability.langsmith.get_current_run_tree",
            lambda: SimpleNamespace(id=run_uuid),
        )
        run_id = capture_run_id()
        assert isinstance(run_id, str)
        assert run_id == str(run_uuid)

    def test_returns_none_without_run_tree(self, monkeypatch):
        monkeypatch.setattr("src.observability.langsmith.get_current_run_tree", lambda: None)
        assert capture_run_id() is None


class TestRouterSanitizers:
    def test_llm_inputs_removes_session(self):
        sanitized = _llm_inputs(
            {
                "messages": [{"role": "user", "content": "hi"}],
                "request_type": "chat",
                "session": object(),  # not JSON-serializable — must be stripped
                "temperature": 0.7,
            }
        )
        assert "session" not in sanitized
        assert sanitized["messages"] == [{"role": "user", "content": "hi"}]
        assert sanitized["request_type"] == "chat"

    def test_llm_outputs_selects_safe_keys(self):
        out = _llm_outputs({"answer": "x", "model": "tinyllama", "usage": {"n": 1}})
        assert out["model"] == "tinyllama"
        assert out["usage"] == {"n": 1}
        assert "answer" not in out  # answer lives in the graph run, not the LLM span


class TestTopicCoverageEvaluator:
    def _run(self, answer):
        return SimpleNamespace(outputs={"answer": answer})

    def test_all_topics_covered(self):
        example = SimpleNamespace(outputs={"expected_topics": ["Cell Theory", "Mitosis"]})
        run = self._run("Cell theory explains mitosis in cells.")
        assert topic_coverage_evaluator(run, example)["score"] == 1.0

    def test_partial_coverage(self):
        example = SimpleNamespace(outputs={"expected_topics": ["Cell Theory", "Mitosis"]})
        run = self._run("Only cell theory.")
        assert topic_coverage_evaluator(run, example)["score"] == 0.5

    def test_empty_expected_is_full_score(self):
        example = SimpleNamespace(outputs={"expected_topics": []})
        assert topic_coverage_evaluator(self._run("anything"), example)["score"] == 1.0


class TestJudgeEvaluatorFactory:
    async def test_llm_judge_evaluator_invokes_judge(self):
        async def fake_score(dimension, question, response, context):
            return {"score": 0.9, "explanation": "good"}

        judge = SimpleNamespace(score=fake_score)
        evaluator = llm_judge_evaluator(SimpleNamespace(name="relevance"), judge=judge)
        result = await evaluator(
            SimpleNamespace(outputs={"answer": "a", "context": "c"}),
            SimpleNamespace(inputs={"question": "q"}),
        )
        assert result == {"key": "relevance", "score": 0.9, "comment": "good"}


class TestSyncDatasets:
    def test_stable_ids_deterministic(self):
        assert _stable_id("ethiobio-curriculum", "cell-theory") == _stable_id(
            "ethiobio-curriculum", "cell-theory"
        )
        assert _stable_id("ethiobio-curriculum", "cell-theory") != _stable_id(
            "ethiobio-gold", "cell-theory"
        )

    def test_gold_set_examples(self, monkeypatch):
        monkeypatch.setattr(
            "src.evaluation.langsmith.sync_datasets._load_gold_set",
            lambda: [
                {
                    "id": "tutor-cell-theory",
                    "question": "What is cell theory?",
                    "expected_answer": "All living things are made of cells",
                }
            ],
        )
        client = SimpleNamespace(
            has_dataset=lambda dataset_name: False,
            create_dataset=lambda name, **kw: SimpleNamespace(id="ds-1"),
        )
        dataset_id, examples = _examples_for(
            {"name": "ethiobio-gold", "description": "gold set", "source": "gold_set"},
            client,
        )
        assert dataset_id == "ds-1"
        assert examples[0]["inputs"]["question"] == "What is cell theory?"
        assert "id" in examples[0]
