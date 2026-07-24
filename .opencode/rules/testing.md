# Testing — EthioBio AI Assistant

Read when: running tests, adding tests, debugging test failures.

## Configuration

- `pytest` with `asyncio_mode = "auto"`, `asyncio_default_test_loop_scope = "module"` (set in `pyproject.toml`)
- `pytest-cov` with 50% floor, `-m "not slow"` for CI
- Rate limiting disabled in tests via `conftest.py` (sets `rate_limit_enabled=False`)
- Chat/lesson-plan endpoint tests marked `@pytest.mark.slow` (excluded from CI — need running LLM)

## Running Tests

```bash
# All unit tests (skip slow endpoint tests needing Ollama)
pytest tests/ -v -k "not slow"

# With coverage
pytest tests/ -v -k "not slow" --cov=src --cov-report=term

# Specific test areas
pytest tests/test_guardrails/ -v               # Guardrail tests
pytest tests/test_agentic_nodes.py -v          # Agentic RAG unit tests
pytest tests/agents/test_planner.py -v         # Planner tests
pytest tests/test_llm.py -v                    # LLM provider tests
pytest tests/test_auth.py -v                   # Auth tests

# Lint & typecheck
ruff check .
mypy src/
```

## Mocking Patterns

- Tests mock `ProviderManager` and `VectorStoreAdapter` via `conftest.py` fixtures (`mock_router`, `mock_retriever`)
- Quiz/lesson tests mock `_call_llm` directly on the agent instance
- Rate limiter tests use `rate_limit_enabled=False` so Redis is optional
- Auth tests test cookie-based JWT flow (sync + async)

## CI Pipeline (GitHub Actions)

Three jobs run on push/PR:

1. **lint+typecheck** — `ruff check . && mypy src/`
2. **test** — `pytest tests/ -v -m "not slow" --cov=src --cov-report=term --cov-fail-under=50`
3. **security** — `pip-audit` + `bandit -r src/`

## Pre-commit Hooks

```bash
pre-commit run --all-files
```

Hooks: ruff lint, ruff format, trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files.
