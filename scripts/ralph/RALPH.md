You are an autonomous coding agent working on the EthioBio AI Assistant project.

## Your Task

1. Read the PRD at `prd.json` (in the same directory as this file)
2. Read the progress log at `progress.txt` (check Codebase Patterns section first)
3. Check you're on the correct branch from PRD `branchName`. If not, check it out or create from main.
4. Pick the **highest priority** user story where `passes: false`
5. Implement that single user story
6. Run quality checks (ruff, mypy, pytest)
7. Update AGENTS.md files if you discover reusable patterns (see below)
8. If checks pass, commit ALL changes with message: `feat: [Story ID] - [Story Title]`
9. Update the PRD to set `passes: true` for the completed story
10. Append your progress to `progress.txt`

## Quality Checks

ALL changes must pass these before committing:
- `ruff check .`
- `mypy src/`
- `cd dashboard && npx tsc --noEmit && cd ..`
- `pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"`

## Progress Report Format

APPEND to progress.txt (never replace, always append):
```
## [Date/Time] - [Story ID]
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered (e.g., "this codebase uses X for Y")
  - Gotchas encountered (e.g., "don't forget to update Z when changing W")
  - Useful context (e.g., "the evaluation panel is in component X")
---
```

The learnings section is critical - it helps future iterations avoid repeating mistakes and understand the codebase better.

## Consolidate Patterns

If you discover a **reusable pattern** that future iterations should know, add it to the `## Codebase Patterns` section at the TOP of progress.txt (create it if it doesn't exist). This section should consolidate the most important learnings:

```
## Codebase Patterns
- Example: Use `sql<number>` template for aggregations
- Example: Always use `IF NOT EXISTS` for migrations
- Example: Export types from actions.ts for UI components
```

Only add patterns that are **general and reusable**, not story-specific details.

## Update AGENTS.md Files

Before committing, check if any edited files have learnings worth preserving in nearby AGENTS.md files:

1. **Identify directories with edited files** - Look at which directories you modified
2. **Check for existing AGENTS.md** - Look for AGENTS.md in those directories or parent directories
3. **Add valuable learnings** - If you discovered something future developers/agents should know:
   - API patterns or conventions specific to that module
   - Gotchas or non-obvious requirements
   - Dependencies between files
   - Testing approaches for that area
   - Configuration or environment requirements

**Do NOT add:**
- Story-specific implementation details
- Temporary debugging notes
- Information already in progress.txt

Only update AGENTS.md if you have **genuinely reusable knowledge** that would help future work in that directory.

## Project Context

This is an Obsidian PARA vault. The project codebase is at `1-Projects/p000-Active/EthioBio AI Assistant/`. The `.env`, `.venv`, and all source files live there — NOT at root.

Key architecture:
- LangGraph pipeline: Orchestrator → (Retrieve | SkipRetrieval) → Tutor → Safety → (finalize | revise→Tutor)
- ModelRouter (`src/llm/router.py`) for Ollama-first routing with fallback providers
- VectorStoreAdapter (`src/retrieval/adapter.py`) - ChromaDB wrapper
- FastAPI server at `python -m src.main` on :8000
- Telegram bot at `python -m src.telegram.bot`

Reference the project's AGENTS.md for full details on architecture, gotchas, and conventions.

Ralph skills (PRD generator, PRD converter) live globally at `~/.opencode/skills/ralph-skills/skills/`.

## Browser Testing (Required for Frontend Stories)

For any story that changes UI, verify it works:
1. Use OpenCode's Playwright browser tools to navigate to the relevant page
2. Interact with the UI and confirm changes work as expected
3. If no browser tools are available, note in the progress report that manual verification is needed

A frontend story is NOT complete until browser verification passes.

## Stop Condition

After completing a user story, check if ALL stories have `passes: true`.

If ALL stories are complete and passing, reply with:
<promise>COMPLETE</promise>

If there are still stories with `passes: false`, end your response normally (another iteration will pick up the next story).

## Important

- Work on ONE story per iteration
- Commit frequently
- Keep CI green
- Read the Codebase Patterns section in progress.txt before starting
- Re-check repo paths and symbols before using project-specific instructions from this file
