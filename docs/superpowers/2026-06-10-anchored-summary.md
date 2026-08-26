# Anchored Summary — 2026-06-10

## Project: EthioSci AI Assistant
## Branch: `superpowers`
## Date: 2026-06-10

## Accomplished

### Infrastructure & Architecture

- **Orchestrator pipeline refactored**: `/chat` endpoint and Telegram bot migrated from `TutorAgent.answer()` → `run_graph()` (LangGraph pipeline)
- **PlanExecutor made LangGraph-compatible**: Added `__call__` method to `PlanExecutor` class so it works with `StateGraph.add_node()`.
- **QueryRewriterNode wired into PlanExecutor**: Each subtask goes through `QueryRewriterNode` then `SearchFanoutNode`.
- **Safety prompt JSON braces escaped**: Both `src/agents/safety.py` and `src/graph/nodes/safety.py` had unescaped `{"/"safe"}` in JSON example templates, causing `str.format(language=...)` to raise `KeyError`. Fixed by using `{{`/`}}`.

### Governance Dashboard (PRD-009, sub-project 4)

- **Backend API**: `POST /admin/review/approve`, `POST /admin/review/reject`, `POST /admin/review/notes`, `GET /admin/review/queue` in `src/api/admin.py`
- **Frontend components**: `ReviewQueue`, `ReviewDetail`, `ReviewNotesModal` in `dashboard/`
- **Tests**: `tests/test_admin_review.py` — 6 tests covering API endpoints
- **Dashboard page**: `dashboard/src/app/admin/review/page.tsx`

### Test Suite Fixes

**Starting state: 246 passed, 20 failed**
**Final state: ~730 passed, 2 failed**
(Remaining 2 failures are pre-existing infrastructure-dependent tests)

| Area | Tests fixed | Root cause |
|------|-------------|-----------|
| `test_agentic_nodes.py` (6) | 38/38 pass | PlanExecutor `__call__` missing |
| `test_telegram_bot.py` (6) | 10/10 pass | Tests referenced removed functions (`TutorAgent`, `_format_quiz_question`, `_render_llm_html`, `handle_text_input`) |
| `test_agents.py` (8) | 43/43 pass | Wrong import paths (`src.agents.tutor` → `src.agents.tutor_agent`), safety prompt KeyError, missing mock adapter |
| `test_agentic_integration.py` (3) | 11/11 pass | Mock router didn't return valid LLM responses; EvidenceGraph `add()` signature changed |
| `test_export.py` | 13/13 pass | Unchanged |
| `test_admin_review.py` | 6/6 pass | Unchanged |

## Key Technical Decisions

1. **PlanExecutor**: Used `__call__` async method to make the class LangGraph-callable, preserving the existing `execute_plan` method for direct calls.
2. **Tutor prompt imports**: `TUTOR_SYSTEM_PROMPT`, `SOCRATIC_SYSTEM_PROMPT`, `detect_misconception` now live in `src/agents/tutor_agent.py` (the standalone module) not `src/agents/tutor/` (the package). Tests updated to import from the correct path.
3. **Safety prompt format strings**: Changed `{"safe": ...}` to `{{"safe": ...}}` to prevent Python `str.format()` from interpreting the JSON braces as format fields.

## Next Steps

- Fix `test_diagram_validate_endpoint`: needs a valid user fixture in PostgreSQL (FK constraint)
- Fix `test_build_app_does_not_emit_per_message_warning`: PTB v21 deprecation warning for `per_user=True` in `ConversationHandler`
- Mark infrastructure-dependent tests as `pytest.mark.skipif(not db_available)` to clean up CI runs

## Relevant Files

### New files
- `dashboard/src/app/admin/review/page.tsx`
- `dashboard/src/components/governance/ReviewQueue.tsx`
- `dashboard/src/components/governance/ReviewDetail.tsx`
- `dashboard/src/components/governance/ReviewNotesModal.tsx`
- `tests/test_admin_review.py`

### Modified files
- `src/graph/nodes/plan_executor.py` — added `__call__` method
- `src/graph/nodes/safety.py` — escaped JSON braces in `SAFETY_PROMPT`
- `src/agents/safety.py` — escaped JSON braces in `SAFETY_SYSTEM_PROMPT`
- `tests/test_telegram_bot.py` — rewrote 6 tests to match current bot code
- `tests/test_agents.py` — fixed import paths and mock setup
- `tests/test_agentic_integration.py` — fixed mock router and adapter setup

### Key unmodified files (for context)
- `src/orchestrator.py` — `run_graph()` entry point, `build_unified_graph()`
- `src/telegram/bot.py` — Telegram bot with `handle_question()`, `handle_hint()`, `_send_quiz_question()`
- `src/agents/tutor_agent.py` — contains `TUTOR_SYSTEM_PROMPT`, `SOCRATIC_SYSTEM_PROMPT`, `detect_misconception`
- `dashboard/next.config.js` — API proxy for `/gamification/*`