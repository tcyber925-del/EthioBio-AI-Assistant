# Testing — EthioBio AI Assistant

Read when: running tests, adding tests, debugging test failures.

## Configuration

- `pytest` with `asyncio_mode = "auto"` (set in `pyproject.toml`)
- No CI, no pre-commit, no integration containers

## Running Tests

```bash
# All unit tests (skips endpoint tests that need Ollama)
pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"

# Fast unit tests (no DB/Ollama)
pytest tests/test_intent_router.py tests/test_heuristic_detector.py tests/test_event_logger.py tests/test_evidence_engine.py -v

# Lint & typecheck
ruff check .
mypy src/
```

## Mocking Patterns

- Tests mock `ProviderManager` and `VectorStoreAdapter` via `conftest.py` fixtures (`mock_router`, `mock_retriever`)
- Quiz/lesson tests mock `_call_llm` directly on the agent instance
- Provider tests (`tests/test_llm.py`) cover `LLMProvider` ABC, `OllamaProvider`, `ModelRegistry`, `ProviderManager`

## Endpoint Tests

- `test_chat_endpoint`, `test_quiz_generate_endpoint` require a running Ollama — excluded from the default test command

## Agentic RAG Tests

```bash
pytest tests/test_agentic_nodes.py -v           # Unit tests (32 tests)
pytest tests/agents/test_planner.py -v          # Planner tests (20 tests)
pytest tests/test_benchmarks.py -v              # Benchmarks (9 tests)
```
