from src.guardrails.action.guard import ToolGuard


def test_allowed_tool():
    g = ToolGuard()
    result = g.validate_tool_call("retrieve_curriculum", {"topic": "cells"})
    assert result.allowed


def test_disallowed_tool():
    g = ToolGuard()
    result = g.validate_tool_call("delete_database", {})
    assert not result.allowed
    assert "not in the allowed list" in result.reason


def test_step_limit():
    g = ToolGuard()
    reasons = g.check_step_limits(tool_call_count=25, step_count=10)
    assert len(reasons) == 1
    assert "Tool call limit" in reasons[0]


def test_response_size_limit():
    g = ToolGuard()
    result = g.check_response("retrieve_curriculum", {}, "x" * 60000)
    assert not result.allowed


def test_quiz_response_keys():
    g = ToolGuard()
    result = g.check_response("generate_quiz", {}, {"questions": [], "title": "Quiz"})
    assert result.allowed


def test_quiz_response_forbidden_keys():
    g = ToolGuard()
    result = g.check_response("generate_quiz", {}, {"exec_command": "rm -rf /"})
    assert not result.allowed
