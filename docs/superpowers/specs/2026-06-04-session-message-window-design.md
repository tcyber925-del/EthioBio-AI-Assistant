# Session Message Window: Raw Conversation History for the LLM

**Date:** 2026-06-04
**Feature:** Persistent Educational Memory — Phase 1
**Approach:** A (Raw messages via existing storage with token-aware sliding window)

## Problem

The LLM pipeline currently injects conversation history only as a text block in the system prompt — last 4 turns, each truncated to 200 characters. The LLM cannot refer back to specific earlier statements, and older context is completely lost within a single session.

## Design

### Flow

```
SessionManager → MemorySession.educational_context["messages"]
                         ↓
              AgentState.messages  (loaded at pipeline start)
                         ↓
              LLM: [system_prompt, msg1, msg2, ..., new_user_msg]
                         ↓
              response appended → saved back to MemorySession
```

### 1. AgentState field

In `src/graph/state.py`:

```python
messages: list[dict] = []
# [{"role": "user" | "assistant", "content": str, "timestamp": str}, ...]
```

### 2. Session storage format

`MemorySession.educational_context["messages"]` stores the same format. Key `"messages"` is preferred over existing `"recent_turns"` for clarity; migration handled by reading either key.

### 3. Token-aware truncation

New utility `src/core/memory/truncation.py`:

```python
CONVERSATION_TOKEN_BUDGET = 3000  # configurable

def truncate_messages(
    messages: list[dict],
    system_prompt: str,
    new_user_message: str,
    budget: int = CONVERSATION_TOKEN_BUDGET,
) -> list[dict]:
    """Drop oldest user/assistant pairs until under token budget."""
```

Token estimation: `len(text) // 4` (rough approximation). The budget applies to all non-system messages — oldest pairs are dropped until the total fits. System message + new user message are always preserved.

### 4. Pipeline wiring

**`src/api/chat.py`** and **`src/api/graph.py`:**
- After `SessionManager.get_or_create_active_session()`, load `messages` from `educational_context`
- Assign to `AgentState.messages` before entering the tutor pipeline
- After LLM call, append `{"role": "assistant", "content": response}` to `AgentState.messages`
- Save back to `MemorySession.educational_context["messages"]`

**`src/telegram/bot.py`:**
- Same pattern: load messages from session, pass to pipeline, save back

### 5. TutorAgent / TutorNode message construction

In `src/agents/tutor.py` and `src/graph/nodes/tutor.py`:

```python
def _build_message_list(
    system_prompt: str,
    history: list[dict],
    user_message: str,
) -> list[dict]:
    truncated = truncate_messages(history, system_prompt, user_message)
    return [
        {"role": "system", "content": system_prompt},
        *truncated,
        {"role": "user", "content": user_message},
    ]
```

### 6. ContextAssembler simplification

The existing `_format_session()` which produced a text block from `recent_turns` becomes redundant for message history. It will still generate "Learner Context" for **profile information** (mastery, summaries, misconceptions) — but the conversation turns section is removed since raw messages now go directly to the LLM.

### 7. Backward compatibility

- Existing `educational_context["recent_turns"]` is read as fallback if `"messages"` is absent
- Empty messages list = new student (no prior conversation)
- Existing `ContextAssembler` text block coexists until deprecated — produces a leaner output

## Files Touched

| File | Change |
|------|--------|
| `src/graph/state.py` | Add `messages: list[dict]` field |
| `src/core/memory/truncation.py` | NEW — `truncate_messages()` utility |
| `src/core/memory/session_manager.py` | Load/save `messages` key |
| `src/core/memory/context_assembler.py` | Remove conversation turns from `_format_session()` |
| `src/agents/tutor.py` | `_build_message_list()` instead of 2-message call |
| `src/graph/nodes/tutor.py` | Same message list construction |
| `src/api/chat.py` | Wire messages through AgentState |
| `src/api/graph.py` | Wire messages through AgentState |
| `src/telegram/bot.py` | Wire messages through session pipeline |

## Testing

- Unit test `truncate_messages()` with known budgets
- Integration test: send 2+ turns to chat endpoint, verify LLM response references prior message content
- Integration test: send 15+ turns to verify oldest messages are dropped
- No new fixtures needed — existing mock session works

## Future (Phase 2)

Cross-session recall: store `ConversationTurn` records per-user per-session, query by topic similarity, inject relevant past turns into the prompt alongside current session messages.
