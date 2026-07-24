# Gotchas — EthioBio AI Assistant

Read when: debugging, getting unexpected behavior, or working in an unfamiliar module.

1. **`topic` filter in RetrievalFilter returns empty** — PDF chunks lack `topic` metadata. Use `grade_level` only; semantic search compensates.

2. **Hint progression shares pattern with socratic_mode** — add field to AgentState → wire through prompts (both TutorAgent and TutorNode) → expose in schemas → add bot UI. Use `_build_system_prompt()` factory pattern for prompt variants.

3. **Telegram rejects HTTP URLs** — use `callback_data` not `url` for inline buttons.

4. **Telegram 4096-char limit** — use `_reply_long()` (at `bot.py:313`) to split responses.

5. **Only one bot instance** — `pkill -f telegram.bot` then `deleteWebhook?drop_pending_updates=true` + `getUpdates?offset=999999999`.

6. **Quiz/Lesson callback patterns must anchor at end**: `^quiz$` not `^quiz` (prevents re-entry from grade buttons).

7. **`telegram_id` must be BIGINT** — large user IDs overflow Integer.

8. **QuizAgent generates from RAG context** — retrieves 5 pgvector chunks, injects into system prompt, instructs LLM to answer strictly from context (see `src/agents/quiz.py:54-58`).

9. **Bidirectional safety revision** — SafetyNode can route `"revise"` or `"reject"` back to TutorNode for regeneration.

10. **`api_base_url` vs `dashboard_url`** — `api_base_url` is for Telegram bot to reach FastAPI backend (`http://app:8000` in Docker). `dashboard_url` is for dashboard links (`http://localhost:3000`).

11. **Ollama model cache** — `OllamaProvider` and `ModelRegistry` both cache model lists. Use `POST /models/refresh` to clear both.

12. **`__model__:` system message convention** — OllamaProvider prepends `__model__:<name>` to system prompt for per-request model selection.

13. **`UsageInfo` TypedDict** — Provider responses include token usage as `UsageInfo` (`prompt_tokens`, `completion_tokens`, `total_tokens`).

14. **Misconception detection is heuristic** — uses `re.split()` sentence splitting + keyword matching on LLM response text. Both TutorAgent and TutorNode have parallel `MISCONCEPTION_INDICATORS` lists and `detect_misconception()` helpers that must stay in sync.

15. **Weak topic detection** — After quiz submit, `analyze_quiz_attempt()` in `src/agents/weak_topic_detection.py` analyzes per-topic scores, updates/creates `StudentMastery` records, detects `MisconceptionPattern` from repeated wrong answers, and syncs `StudentProfile.weak_areas`/`topic_mastery`. Wire into endpoint AFTER gamification, BEFORE session.commit().

16. **`QuizAttempt.answers` is `Mapped[dict]` but stores list data** — when accessing, safely cast with `cast(list[Any], raw) if isinstance(raw, list) else []` to satisfy mypy.

17. **`send_email()` silently returns False when unconfigured** — No error is raised if `email_host` is unset. Always check the return value or log the result.

18. **NotificationPreference has a 1:1 user_id PK** — No separate `id` column; `user_id` is the PK. Upsert on conflict or check existence before `PUT`.

19. **Milestone email fires at 10% progress intervals** — `MILESTONE_EMAIL_THRESHOLD = 10.0` means alert triggers at 10%, 20%, 30%, etc. — not at every individual task completion.

20. **Adaptive quiz requires user_id for topic ability lookup** — `select_adaptive_questions()` falls back to random selection when `user_id` is not provided; adaptive mode only works when both `adaptive=true` and `user_id` are set.

21. **`requires_planning` gates Agentic RAG** — OrchestratorNode derives `requires_planning` from `subtasks` count, NOT from intent. Use `build_unified_graph()` for production.

22. **PlannerAgent requires `objective` field** — `Plan` model uses `objective` (not `query`); `ComplexityLevel` uses LOW/MEDIUM/HIGH enum values.

23. **QueryRewriter uses LLM with heuristic fallback** — When `router` is provided, uses LLM for rewriting; falls back to heuristic expansion. Check `retrieval_metadata["method"]` for "llm" or "heuristic".

24. **SearchFanout uses parallel retrieval** — Executes all index-query combinations concurrently via `asyncio.gather()`. Fallback to sequential on error.

25. **EvidenceGraph stores full chunk content** — Per ADR-0001, evidence records store complete text (not just IDs) for auditability. `EvidenceRecord` is defined in `src/database/models.py`.
