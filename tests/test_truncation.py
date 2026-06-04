import pytest
from src.core.memory.truncation import truncate_messages


class TestTruncateMessages:
    def test_empty_history(self):
        result = truncate_messages(
            messages=[],
            system_prompt="You are a tutor.",
            new_user_message="What is a cell?",
            budget=1000,
        )
        assert result == []

    def test_within_budget_returns_all(self):
        messages = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
        result = truncate_messages(
            messages=messages,
            system_prompt="You are a tutor.",
            new_user_message="What is a cell?",
            budget=1000,
        )
        assert result == messages

    def test_exceeding_budget_drops_oldest_pairs(self):
        messages = [
            {"role": "user", "content": "X" * 40},
            {"role": "assistant", "content": "Y" * 40},
            {"role": "user", "content": "X" * 40},
            {"role": "assistant", "content": "Y" * 40},
        ]
        result = truncate_messages(
            messages=messages,
            system_prompt="You are a tutor.",
            new_user_message="Z",
            budget=25,
        )
        assert len(result) == 2
        assert result[0]["content"] == "X" * 40
        assert result[1]["content"] == "Y" * 40

    def test_budget_under_one_message_keeps_at_least_newest(self):
        messages = [
            {"role": "user", "content": "Old question?"},
            {"role": "assistant", "content": "Old answer."},
            {"role": "user", "content": "New question?"},
            {"role": "assistant", "content": "New answer."},
        ]
        result = truncate_messages(
            messages=messages,
            system_prompt="x",
            new_user_message="z",
            budget=1,
        )
        assert len(result) >= 1
        assert result[-1]["content"] == "New answer."
