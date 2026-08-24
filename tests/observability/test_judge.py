"""Regression tests for LLMJudge output parsing.

Guards against the production failure where the judge model returned empty or
prose-wrapped output and every dimension logged
eval_score_failed "Expecting value: line 1 column 1 (char 0)", zeroing scores.
"""

from src.observability.evaluation.dimensions import DIMENSIONS
from src.observability.evaluation.judge import LLMJudge


class _FakeRouter:
    def __init__(self, content):
        self._content = content

    async def route(self, **kwargs):
        return {"content": self._content, "model": "fake", "confidence": 1.0, "usage": {}}


def _judge(content) -> LLMJudge:
    return LLMJudge(router=_FakeRouter(content))


_DIM = DIMENSIONS[0]  # faithfulness


async def test_parses_code_fenced_json():
    judge = _judge('```json\n{"score": 0.8, "explanation": "well grounded"}\n```')
    result = await judge.score(_DIM, question="q", response="r", context="c")
    assert result == {"score": 0.8, "explanation": "well grounded"}


async def test_extracts_json_from_prose_without_fences():
    judge = _judge(
        'My evaluation: {"score": 0.7, "explanation": "mostly supported"} Hope this helps!'
    )
    result = await judge.score(_DIM, question="q", response="r", context="c")
    assert result["score"] == 0.7
    assert result["explanation"] == "mostly supported"


async def test_extracts_json_with_trailing_text_after_object():
    judge = _judge('{"score": 0.6, "explanation": "ok"} That is my assessment.')
    result = await judge.score(_DIM, question="q", response="r", context="c")
    assert result["score"] == 0.6


async def test_empty_content_returns_graceful_zero():
    judge = _judge("")
    result = await judge.score(_DIM, question="q", response="r", context="c")
    assert result["score"] == 0.0
    assert "failed" in result["explanation"].lower()


async def test_score_clamped_to_unit_range():
    judge = _judge('{"score": 5.0, "explanation": "overconfident"}')
    result = await judge.score(_DIM, question="q", response="r", context="c")
    assert result["score"] == 1.0
