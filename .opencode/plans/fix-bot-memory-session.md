# Fix: Telegram Bot Memory Session Leak

## Bug

`_build_memory_context` opens a DB session with `async with factory() as db:` and returns `db`. When the function returns, Python exits the async context manager, calling `await db.close()`. The returned `_mem_db` is closed. The turn-saving code at `bot.py:448-462` tries to `execute()` on the closed session, silently fails, and conversation turns are never persisted.

## Changes

### 1. `_build_memory_context` — accept `db` param, remove self-managed session

```python
# BEFORE
async def _build_memory_context(telegram_id: int, topic: str | None):
    """..."""
    session_mgr = SessionManager()
    assembler = ContextAssembler()
    factory = async_session_factory()
    async with factory() as db:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if not user:
            return None, None, "", db
        mem_session = await session_mgr.get_or_create_active_session(
            user.id, topic=topic, db=db,
        )
        ctx = await assembler.assemble(
            user_id=user.id, topic=topic, db=db,
            session_state={...} if mem_session else None,
            socratic_state=None,
        )
        return user.id, mem_session.session_id if mem_session else None, ctx, db
```

```python
# AFTER
async def _build_memory_context(telegram_id: int, topic: str | None, db):
    """..."""
    session_mgr = SessionManager()
    assembler = ContextAssembler()
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        return None, None, ""
    mem_session = await session_mgr.get_or_create_active_session(
        user.id, topic=topic, db=db,
    )
    ctx = await assembler.assemble(
        user_id=user.id, topic=topic, db=db,
        session_state={...} if mem_session else None,
        socratic_state=None,
    )
    return user.id, mem_session.session_id if mem_session else None, ctx
```

### 2. `handle_question` — open session at the top, wrap the read + write

```python
# BEFORE
    result = None
    memory_user_id = None
    memory_session_id = None
    memory_context = ""
    _mem_db = None
    try:
        telegram_id = ...
        if telegram_id:
            memory_user_id, memory_session_id, memory_context, _mem_db = await _build_memory_context(...)
        ...
        if _mem_db and memory_user_id and memory_session_id:  # _mem_db is closed!
            try:
                mem_session = (await _mem_db.execute(...))  # FAILS
                ...
```

```python
# AFTER
    result = None
    memory_user_id = None
    memory_session_id = None
    memory_context = ""
    try:
        telegram_id = update.effective_user.id if update.effective_user else None
        async with async_session_factory() as _mem_db:
            if telegram_id:
                memory_user_id, memory_session_id, memory_context = await _build_memory_context(
                    telegram_id, ... , _mem_db,
                )
            ... agent.answer() ...
            if memory_user_id and memory_session_id:
                try:
                    mem_session = (await _mem_db.execute(...))  # WORKS — session open
                    ...
                    await _mem_db.commit()
```

3-line removals: `result = None; ... _mem_db = None` → `_mem_db` is now managed by `async with`.
