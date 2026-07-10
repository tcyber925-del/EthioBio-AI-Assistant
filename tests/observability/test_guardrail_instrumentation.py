"""Tests for the guardrail instrumentation decorator."""

import pytest

from src.observability.guardrail_instrumentation import (
    _is_triggered,
    observe_guardrail,
)


class DummyWithFlagged:
    def __init__(self, v: bool):
        self.flagged = v


class DummyWithBlocked:
    def __init__(self, v: bool):
        self.blocked = v


class DummyWithDetected:
    def __init__(self, v: bool):
        self.detected = v


class DummyWithPassed:
    def __init__(self, v: bool):
        self.passed = v


class DummyWithOnTopic:
    def __init__(self, v: bool):
        self.on_topic = v


class DummyWithAllowed:
    def __init__(self, v: bool):
        self.allowed = v


class TestIsTriggered:
    def test_none(self):
        assert not _is_triggered(None)

    def test_bool_true(self):
        assert _is_triggered(True)

    def test_bool_false(self):
        assert not _is_triggered(False)

    def test_flagged_true(self):
        assert _is_triggered(DummyWithFlagged(True))

    def test_flagged_false(self):
        assert not _is_triggered(DummyWithFlagged(False))

    def test_blocked_true(self):
        assert _is_triggered(DummyWithBlocked(True))

    def test_blocked_false(self):
        assert not _is_triggered(DummyWithBlocked(False))

    def test_detected_true(self):
        assert _is_triggered(DummyWithDetected(True))

    def test_passed_false(self):
        assert _is_triggered(DummyWithPassed(False))

    def test_passed_true(self):
        assert not _is_triggered(DummyWithPassed(True))

    def test_on_topic_false(self):
        assert _is_triggered(DummyWithOnTopic(False))

    def test_on_topic_true(self):
        assert not _is_triggered(DummyWithOnTopic(True))

    def test_allowed_false(self):
        assert _is_triggered(DummyWithAllowed(False))

    def test_dict_triggered(self):
        assert _is_triggered({"triggered": True})

    def test_dict_flagged(self):
        assert _is_triggered({"flagged": True})

    def test_dict_blocked(self):
        assert _is_triggered({"blocked": True})

    def test_dict_not_triggered(self):
        assert not _is_triggered({"ok": True})


class TestObserveGuardrailDecorator:
    def test_sync_decorated_function_runs(self):
        @observe_guardrail(module="test_sync", guardrail_type="input")
        def my_func(x: int) -> int:
            return x * 2

        assert my_func(3) == 6

    @pytest.mark.asyncio
    async def test_async_decorated_function_runs(self):
        @observe_guardrail(module="test_async", guardrail_type="output")
        async def my_func(x: int) -> int:
            return x * 2

        assert await my_func(3) == 6

    def test_preserves_function_name(self):
        @observe_guardrail(module="m", guardrail_type="output")
        def my_special_func():
            pass

        assert my_special_func.__name__ == "my_special_func"

    def test_raises_on_error(self):
        @observe_guardrail(module="m", guardrail_type="output")
        def broken():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            broken()

    def test_int_result_not_triggered(self):
        """Integer return should not be considered triggered."""

        @observe_guardrail(module="m", guardrail_type="output")
        def returns_int():
            return 42

        assert returns_int() == 42

    def test_sanitize_type_return_not_triggered(self):
        """String return from sanitize should not be considered triggered."""

        @observe_guardrail(module="input_sanitizer", guardrail_type="input")
        def sanitize(text: str) -> str:
            return text.strip()

        result = sanitize("  hello  ")
        assert result == "hello"
