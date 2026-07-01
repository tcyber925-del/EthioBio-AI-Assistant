from src.observability.structured_logging import log_event


class TestLogEvent:
    def test_basic_event(self):
        result = log_event(
            event="test_event",
            domain="testing",
            module="test_module",
            outcome="passed",
            duration_ms=10.0,
        )
        assert result["domain"] == "testing"
        assert result["module"] == "test_module"
        assert result["outcome"] == "passed"
        assert result["duration_ms"] == 10.0

    def test_event_with_optional_fields(self):
        result = log_event(
            event="test",
            domain="d",
            module="m",
            outcome="failed",
            duration_ms=5.0,
            user_id="user_123",
            details={"error": "timeout"},
            level="error",
        )
        assert result["user_id"] == "user_123"
        assert result["details"] == {"error": "timeout"}

    def test_event_without_duration(self):
        result = log_event(
            event="simple",
            domain="d",
            module="m",
            outcome="ok",
        )
        assert "duration_ms" not in result
