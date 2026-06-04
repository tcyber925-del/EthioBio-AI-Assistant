CONVERSATION_TOKEN_BUDGET = 3000


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def truncate_messages(
    messages: list[dict],
    budget: int = CONVERSATION_TOKEN_BUDGET,
) -> list[dict]:
    """Drop oldest user/assistant pairs until remaining messages fit within budget."""
    if not messages:
        return []

    total = sum(estimate_tokens(m.get("content", "")) for m in messages)

    if total <= budget:
        return messages

    result = list(messages)
    while len(result) >= 2 and sum(estimate_tokens(m.get("content", "")) for m in result) > budget:
        result.pop(0)
        result.pop(0)

    if len(result) % 2 != 0:
        result.pop(0)

    if not result and messages:
        result = [messages[-1]]

    return result
