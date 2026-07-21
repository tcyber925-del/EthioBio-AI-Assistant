# Anchored Summary — Streaming + Persistence + Sidebar

## Completed

### Streaming (SSE)
- All 4 providers (Ollama, OpenAI, Anthropic, OpenRouter) stream tokens via `asyncio.Queue` + `StreamingResponse(text/event-stream)`
- Only 1 `done: true` event per request (intermediate duplicate from `TutorNode._legacy_call` skipped)
- Metadata (`model_used`, `confidence`, `sources`, `xp_awarded`, `level_up`) sent with final event
- Web UI consumes SSE via `streamFetch()` in `dashboard/src/lib/fetch.ts`
- Telegram bot `_stream_and_edit()` with 400ms flush

### Persistence
- `_persist_chat_history()` extracts full save logic from blocking path and calls it after graph completes
- Savepoint (`begin_nested()`) in `CrossSessionRecall.record_turns` isolates FK failures from the outer transaction — prevents `PendingRollbackError` cascade
- Separate-session `record_turns` runs after main `session.commit()` as best-effort
- MemorySession `set_messages()` + `heartbeat()` + XP/streak/achievements all persist correctly

### Sidebar (Conversation History)
- `/api/v1/memory/conversations` falls back to `MemorySession.educational_context["messages"]` when `ConversationTurn` table is empty
- Verified: MemorySession messages persist correctly (local test shows 2 messages in educational_context)
- `ConversationTurn` records work locally (8 records) but silently fail on Railway due to FK issue

### Deployment
- Railway auto-deploys from `main`; 7+ successful deploys of streaming + persistence code
- Vercel auto-deploys dashboard from `main` with conditional `output: 'standalone'`
- Local Docker container (`ethiobio-app`) updated via `docker cp` for rapid iteration
- `output: 'standalone'` made conditional on `!process.env.VERCEL`

## Open Issues

### ConversationTurn FK Violation on Railway
**Root cause**: `MemorySession` row does not persist in PostgreSQL even though `session.commit()` returns without error. Confirmed via debug logging: `turn_session.get(MemorySession, mem_session.session_id)` returns `None` **after** commit. 
**Impact**: `ConversationTurn` inserts silently fail with FK error. Sidebar fallback reads from `MemorySession.educational_context["messages"]` instead.
**Next steps**: Needs Railway support or direct DB inspection to understand why committed MemorySession rows are invisible to new transactions.

## Relevant Files
- `src/api/chat.py`: `_handle_chat_stream`, `_stream_events`, `_persist_chat_history`
- `src/api/memory.py`: `get_recent_conversations` with MemorySession fallback
- `src/core/memory/cross_session_recall.py`: `record_turns` with savepoint
- `src/core/memory/session_manager.py`: `get_or_create_active_session`, `heartbeat`, `set_messages`
- `src/database/models.py`: `MemorySession`, `ConversationTurn`
- `src/schemas/streaming.py`: `TokenChunk`
- `dashboard/src/lib/fetch.ts`: `streamFetch()` SSE consumer
- `dashboard/src/app/(dashboard)/ask/page.tsx`: streaming ask page
