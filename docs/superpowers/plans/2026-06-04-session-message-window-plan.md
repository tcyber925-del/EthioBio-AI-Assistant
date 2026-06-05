# Session Message Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pass raw conversation message history to the LLM within a session instead of a compressed text block in the system prompt.

**Architecture:** Add `messages` field to AgentState loaded from `MemorySession.educational_context`. Build LLM message list as `[system, ...history, new_user_message]` with token-aware truncation dropping oldest pairs when over budget. Save back after each turn.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy async, LangGraph, pytest

---

### Task 1: Truncation utility

**Files:**
- Create: `src/core/memory/truncation.py`
- Test: `tests/test_truncation.py`

- [ ] **Step 1: Write the failing test**

```python
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
        # Each message ~40 chars → ~10 tokens each
        messages = [
            {"role": "user", "content": "X" * 40},
            {"role": "assistant", "content": "Y" * 40},
            {"role": "user", "content": "X" * 40},
            {"role": "assistant", "content": "Y" * 40},
        ]
        # Budget 25 tokens → only fits 2 messages (system + new user always kept outside)
        result = truncate_messages(
            messages=messages,
            system_prompt="You are a tutor.",
            new_user_message="Z",
            budget=25,
        )
        # Should drop oldest 2 messages (1 pair), keep newest 2
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
        # Budget too small for even 1 message — should still keep at least newest
        result = truncate_messages(
            messages=messages,
            system_prompt="x",
            new_user_message="z",
            budget=1,
        )
        assert len(result) >= 1
        assert result[-1]["content"] == "New answer."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_truncation.py::TestTruncateMessages -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.core.memory.truncation'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/core/memory/truncation.py

CONVERSATION_TOKEN_BUDGET = 3000


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def truncate_messages(
    messages: list[dict],
    system_prompt: str,
    new_user_message: str,
    budget: int = CONVERSATION_TOKEN_BUDGET,
) -> list[dict]:
    """Drop oldest user/assistant pairs until remaining messages fit within budget.

    The budget applies only to the `messages` (history) — system prompt and
    new_user_message token counts are NOT subtracted from this budget (they
    are always prepended/appended by the caller).
    """
    if not messages:
        return []

    total = sum(estimate_tokens(m.get("content", "")) for m in messages)

    if total <= budget:
        return messages

    # Drop oldest pairs (user+assistant) until under budget
    result = list(messages)
    while len(result) >= 2 and sum(estimate_tokens(m.get("content", "")) for m in result) > budget:
        result.pop(0)
        result.pop(0)

    # If dropping pairs left an odd message (orphaned user), also drop it
    if len(result) % 2 != 0:
        result.pop(0)

    # Always keep at least the most recent message
    if not result and messages:
        result = [messages[-1]]

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_truncation.py::TestTruncateMessages -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_truncation.py src/core/memory/truncation.py
git commit -m "feat: add token-aware message truncation utility"
```

---

### Task 2: Add `messages` field to AgentState

**Files:**
- Modify: `src/graph/state.py`

- [ ] **Step 1: Add the field**

```python
# After line 68 (learner_profile_block)
messages: list[dict] = field(default_factory=list)
```

- [ ] **Step 2: Run lint check**

Run: `ruff check src/graph/state.py`
Expected: clean (no new errors)

- [ ] **Step 3: Commit**

```bash
git add src/graph/state.py
git commit -m "feat: add messages field to AgentState for conversation history"
```

---

### Task 3: Load/save messages in SessionManager

**Files:**
- Modify: `src/core/memory/session_manager.py`

- [ ] **Step 1: Update `_format_session` — no changes needed here**

The session manager itself doesn't format messages — that's `ContextAssembler`. But we need to ensure the `messages` key is loaded and saved. The session manager already handles `educational_context` dict. The messages will be stored in `educational_context["messages"]`.

Add a helper for extracting messages:

```python
# In src/core/memory/session_manager.py, add after close_session:

    def get_messages(self, session: MemorySession) -> list[dict]:
        """Get conversation messages from session educational_context."""
        ctx = session.educational_context
        if not isinstance(ctx, dict):
            return []
        messages = ctx.get("messages")
        if isinstance(messages, list):
            return messages
        # Fallback: migrate from old "recent_turns"
        recent = ctx.get("recent_turns")
        if isinstance(recent, list):
            # recent_turns already has same format
            return recent
        return []

    def set_messages(self, session: MemorySession, messages: list[dict]) -> None:
        """Store conversation messages in session educational_context."""
        if not isinstance(session.educational_context, dict):
            session.educational_context = {}
        session.educational_context["messages"] = messages
```

- [ ] **Step 2: Run lint check**

Run: `ruff check src/core/memory/session_manager.py`
Expected: clean

- [ ] **Step 3: Commit**

```bash
git add src/core/memory/session_manager.py
git commit -m "feat: add get_messages/set_messages helpers to SessionManager"
```

---

### Task 4: Remove conversation turns from ContextAssembler

**Files:**
- Modify: `src/core/memory/context_assembler.py`

- [ ] **Step 1: Remove recent_turns formatting from `_format_session`**

Since raw messages now go directly to the LLM, the conversation turns in the context block are redundant. Remove the `recent_turns` section from `_format_session`:

```python
    def _format_session(self, state: dict | None) -> str:
        if not state:
            return ""
        lines = [
            f"- Topic: {state.get('active_topic', 'unknown')}",
            f"- Mode: {state.get('tutoring_mode', 'direct')}",
        ]

        ctx = state.get("educational_context")
        if isinstance(ctx, dict):
            # Only include non-message context keys
            ctx_text = {k: v for k, v in ctx.items() if k not in ("messages", "recent_turns")}
            if ctx_text:
                lines.append(f"- Educational Context: {ctx_text}")

        questions = state.get("unresolved_questions")
        if questions and isinstance(questions, list) and len(questions) > 0:
            lines.append(f"- Unresolved Questions: {'; '.join(str(q) for q in questions[:3])}")
        return "\n".join(lines)
```

- [ ] **Step 2: Run lint check**

Run: `ruff check src/core/memory/context_assembler.py`
Expected: clean

- [ ] **Step 3: Commit**

```bash
git add src/core/memory/context_assembler.py
git commit -m "refactor: remove conversation turns from ContextAssembler (now in raw messages)"
```

---

### Task 5: Build message list in TutorAgent

**Files:**
- Modify: `src/agents/tutor.py`

- [ ] **Step 1: Add `messages` parameter to `answer()` and build message list**

Change `TutorAgent.answer()` to accept and pass message history:

```python
    async def answer(
        self,
        question: str,
        user_id: UUID,
        grade_level: Optional[int] = None,
        topic: Optional[str] = None,
        language: str = "en",
        use_rag: bool = True,
        session: Optional[AsyncSession] = None,
        socratic_mode: bool = False,
        hint_level: int = 0,
        reveal_answer: bool = False,
        memory_context: str = "",
        learner_profile_block: str = "",
        messages: list[dict] | None = None,  # NEW
    ) -> dict:
```

At the bottom of the method, replace the `_call_llm` call with message list construction:

```python
        from src.core.memory.truncation import truncate_messages

        history = truncate_messages(messages or [], system_prompt, user_message)

        llm_messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ]

        result = await self._call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            session=session,
            request_type="tutor",
        )
```

Wait — `_call_llm` only accepts `system_prompt` and `user_message`. I need to either:
a) Change `_call_llm` to accept a full message list, or
b) Call `self.llm_router.route()` directly with the full message list

Option b is simpler and doesn't break anything:

```python
        result = await self.llm_router.route(
            messages=llm_messages,
            request_type="tutor",
            session=session,
            temperature=0.7,
            max_tokens=2048,
        )
```

- [ ] **Step 2: Implement the change**

The full updated bottom of `answer()`:

```python
        from src.core.memory.truncation import truncate_messages

        user_message = f"[Grade{grade_context}] {lang_context}\n\nStudent question: {question}"

        history = truncate_messages(messages or [], system_prompt, user_message)

        llm_messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_message},
        ]

        result = await self.llm_router.route(
            messages=llm_messages,
            request_type="tutor",
            session=session,
            temperature=0.7,
            max_tokens=2048,
        )
```

And remove the old `result = await self._call_llm(...)` block at lines 176-181.

- [ ] **Step 3: Run lint check**

Run: `ruff check src/agents/tutor.py`
Expected: clean

- [ ] **Step 4: Commit**

```bash
git add src/agents/tutor.py
git commit -m "feat: pass conversation history as raw messages to LLM in TutorAgent"
```

---

### Task 6: Build message list in TutorNode

**Files:**
- Modify: `src/graph/nodes/tutor.py`

- [ ] **Step 1: Insert message history into the messages list**

Replace the current messages construction at lines 127-130:

```python
        from src.core.memory.truncation import truncate_messages

        history = truncate_messages(state.messages, system, user_message)

        messages = [
            {"role": "system", "content": system},
            *history,
            {"role": "user", "content": user_message},
        ]
```

- [ ] **Step 2: Run lint check**

Run: `ruff check src/graph/nodes/tutor.py`
Expected: clean

- [ ] **Step 3: Commit**

```bash
git add src/graph/nodes/tutor.py
git commit -m "feat: pass conversation history as raw messages in TutorNode"
```

---

### Task 7: Wire messages through chat.py

**Files:**
- Modify: `src/api/chat.py`

- [ ] **Step 1: Load messages from session, pass to agent, save back**

Replace the current session/turns handling (lines 30-48 and 75-82) with:

```python
        mem_session = None
        memory_context = ""
        conversation_messages: list[dict] = []
        if request.user_id:
            mem_session = await session_manager.get_or_create_active_session(
                request.user_id, topic=request.topic, db=session,
            )
            if mem_session:
                conversation_messages = session_manager.get_messages(mem_session)
                memory_context = await context_assembler.assemble(
                    user_id=request.user_id,
                    topic=request.topic,
                    db=session,
                    session_state={
                        "active_topic": mem_session.active_topic,
                        "tutoring_mode": mem_session.tutoring_mode,
                        "educational_context": mem_session.educational_context,
                        "unresolved_questions": mem_session.unresolved_questions,
                    } if mem_session else None,
                    socratic_state=None,
                )
```

And in the `agent.answer()` call, add `messages=conversation_messages`:

```python
        result = await agent.answer(
            question=request.question,
            user_id=request.user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=request.language,
            use_rag=request.use_rag,
            session=session,
            socratic_mode=request.socratic_mode,
            hint_level=request.hint_level,
            reveal_answer=request.reveal_answer,
            memory_context=memory_context,
            learner_profile_block=learner_profile_block,
            messages=conversation_messages,
        )
```

Replace the old turn-saving block (lines 75-82) with:

```python
        if mem_session:
            conversation_messages.append({"role": "user", "content": request.question})
            if result["answer"]:
                conversation_messages.append({"role": "assistant", "content": result["answer"]})
            session_manager.set_messages(mem_session, conversation_messages[-20:])
```

- [ ] **Step 2: Run lint check**

Run: `ruff check src/api/chat.py`
Expected: clean

- [ ] **Step 3: Commit**

```bash
git add src/api/chat.py
git commit -m "feat: wire conversation messages through chat endpoint"
```

---

### Task 8: Wire messages through graph.py

**Files:**
- Modify: `src/api/graph.py`

- [ ] **Step 1: Load messages, pass to run_graph, save back**

Replace the session loading (lines 69-98) to also load messages:

```python
        mem_session = None
        socratic_state_rec = None
        conversation_messages: list[dict] = []
        if request.user_id:
            mem_session = await session_manager.get_or_create_active_session(
                request.user_id, topic=request.topic, db=db,
            )
            if mem_session:
                conversation_messages = session_manager.get_messages(mem_session)
            if request.socratic_mode and request.topic:
                socratic_state_rec = await socratic_manager.get_state(
                    request.user_id, request.topic, db,
                )
```

Add `messages=conversation_messages` to the `run_graph()` call:

```python
        result = await run_graph(
            user_message=request.question,
            user_id=request.user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=request.language,
            preferred_model=request.model,
            socratic_mode=request.socratic_mode,
            hint_level=request.hint_level,
            reveal_answer=request.reveal_answer,
            session_id=str(mem_session.session_id) if mem_session else None,
            memory_context=memory_context,
            learner_profile_block=learner_profile_block,
            socratic_stage=socratic_state_rec.socratic_stage if socratic_state_rec else "",
            socratic_focus=socratic_state_rec.current_focus if socratic_state_rec else "",
            socratic_understanding=(
                socratic_state_rec.student_understanding if socratic_state_rec else ""
            ),
            socratic_next_question=socratic_state_rec.next_question if socratic_state_rec else "",
            messages=conversation_messages,  # NEW
        )
```

Replace the old turn-saving block (lines 144-163) with:

```python
        if mem_session:
            conversation_messages.append({"role": "user", "content": request.question})
            if result.answer:
                conversation_messages.append({"role": "assistant", "content": result.answer})
            session_manager.set_messages(mem_session, conversation_messages[-20:])
```

Also update orchestrator.py `run_graph()` function signature to accept and pass `messages`:

```python
async def run_graph(
    user_message: str,
    user_id=None,
    grade_level: int = None,
    topic: str = None,
    language: str = "en",
    preferred_model: str | None = None,
    socratic_mode: bool = False,
    hint_level: int = 0,
    reveal_answer: bool = False,
    session_id: str | None = None,
    memory_context: str = "",
    learner_profile_block: str = "",
    socratic_stage: str = "",
    socratic_focus: str = "",
    socratic_understanding: str = "",
    socratic_next_question: str = "",
    messages: list[dict] | None = None,  # NEW
) -> GraphOutput:
```

And pass it to `AgentState(...)`:

```python
    initial_state = AgentState(
        user_message=user_message,
        user_id=user_id,
        grade_level=grade_level,
        topic=topic,
        language=language,
        preferred_model=preferred_model or "",
        session_id=session_id,
        memory_context=memory_context,
        learner_profile_block=learner_profile_block,
        use_learner_awareness=bool(learner_profile_block),
        socratic_mode=socratic_mode,
        hint_level=hint_level,
        reveal_answer=reveal_answer,
        socratic_stage=socratic_stage,
        socratic_focus=socratic_focus,
        socratic_understanding=socratic_understanding,
        socratic_next_question=socratic_next_question,
        messages=messages or [],  # NEW
    )
```

- [ ] **Step 2: Run lint check**

Run: `ruff check src/api/graph.py src/graph/orchestrator.py`
Expected: clean

- [ ] **Step 3: Commit**

```bash
git add src/api/graph.py src/graph/orchestrator.py
git commit -m "feat: wire conversation messages through graph endpoint"
```

---

### Task 9: Wire messages through Telegram bot

**Files:**
- Modify: `src/telegram/bot.py`

- [ ] **Step 1: Update `_build_memory_context` to also return messages**

```python
async def _build_memory_context(telegram_id: int, topic: str | None, db):
    """Look up user, create/get active session, build memory context."""
    topic = str(topic) if topic is not None else None
    session_mgr = SessionManager()
    assembler = ContextAssembler()
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        return None, None, "", []
    mem_session = await session_mgr.get_or_create_active_session(
        user.id, topic=topic, db=db,
    )
    ctx = await assembler.assemble(
        user_id=user.id, topic=topic, db=db,
        session_state={
            "active_topic": mem_session.active_topic,
            "tutoring_mode": mem_session.tutoring_mode,
            "educational_context": mem_session.educational_context,
            "unresolved_questions": mem_session.unresolved_questions,
        } if mem_session else None,
        socratic_state=None,
    )
    messages = session_mgr.get_messages(mem_session) if mem_session else []
    return user.id, mem_session.session_id if mem_session else None, ctx, messages
```

- [ ] **Step 2: Update every call site of `_build_memory_context`**

There are 4 call sites in bot.py (lines ~490, 562, 611, 839). Each one needs to:

a) Accept the new 4th return value:
```python
memory_user_id, memory_session_id, memory_context, conversation_messages = await _build_memory_context(...)
```

b) Pass `messages=conversation_messages` to `agent.answer()`.

c) Save messages back after the response:
```python
if memory_user_id and memory_session_id:
    try:
        mem_session = (await _mem_db.execute(
            select(MemorySession).where(MemorySession.session_id == memory_session_id)
        )).scalar_one_or_none()
        if mem_session:
            conversation_messages.append({"role": "user", "content": question})
            conversation_messages.append({"role": "assistant", "content": result["answer"]})
            session_manager.set_messages(mem_session, conversation_messages[-20:])
            await _mem_db.commit()
    except Exception as e:
        logger.warning("memory_turns_save_error", error=str(e))
```

- [ ] **Step 3: Run lint check**

Run: `ruff check src/telegram/bot.py`
Expected: clean

- [ ] **Step 4: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat: wire conversation messages through Telegram bot"
```

---

### Task 10: Integration verification

- [ ] **Step 1: Run the full test suite (skip integration)**

Run: `pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint" 2>&1 | tail -20`
Expected: all tests pass

- [ ] **Step 2: Run lint on all modified files**

Run: `ruff check src/core/memory/truncation.py src/graph/state.py src/core/memory/session_manager.py src/core/memory/context_assembler.py src/agents/tutor.py src/graph/nodes/tutor.py src/api/chat.py src/api/graph.py src/graph/orchestrator.py`
Expected: clean (pre-existing errors in admin.py not related)

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: finalize session message window implementation"
```
