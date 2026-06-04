from src.core.memory.truncation import estimate_tokens, truncate_messages


class TestTruncateMessages:
    def test_empty_history(self):
        result = truncate_messages(messages=[], budget=1000)
        assert result == []

    def test_within_budget_returns_all(self):
        messages = [
            {"role": "user", "content": "a"},
            {"role": "assistant", "content": "b"},
        ]
        result = truncate_messages(messages=messages, budget=1000)
        assert result == messages

    def test_exceeding_budget_drops_oldest_pairs(self):
        messages = [
            {"role": "user", "content": "X" * 40},
            {"role": "assistant", "content": "Y" * 40},
            {"role": "user", "content": "X" * 40},
            {"role": "assistant", "content": "Y" * 40},
        ]
        result = truncate_messages(messages=messages, budget=25)
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
        result = truncate_messages(messages=messages, budget=1)
        assert len(result) >= 1
        assert result[-1]["content"] == "New answer."


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 1

    def test_short_text(self):
        assert estimate_tokens("abc") == 1

    def test_typical_text(self):
        text = "hello world how are you doing today"
        assert estimate_tokens(text) == len(text) // 4

    def test_missing_content_key(self):
        messages = [
            {"role": "user"},
            {"role": "user", "content": "hello"},
        ]
        result = truncate_messages(messages=messages, budget=1000)
        assert len(result) == 2
