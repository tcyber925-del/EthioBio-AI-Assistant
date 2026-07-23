# Track 2 — CI & Testing Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix broken API tests, restore CI to run meaningful tests, enable stricter linting/types, add coverage tracking.

**Architecture:** Tiered test markers (smoke/integration/slow), pytest-cov with 50% floor, stricter ruff + mypy, pre-commit hooks.

**Tech Stack:** pytest, ruff, mypy, GitHub Actions, pre-commit

---

### Task 1: Fix API tests that accept 500

**Files:**
- Modify: All API test files with `status_code in (200, 500)`

- [ ] **Step 1: Find all broken assertions**

Run: `rg "in \(200, 500\)" tests/ --files-with-matches`

- [ ] **Step 2: Fix each one to assert specific expected code**

Example fix pattern:

```python
# Before:
assert response.status_code in (200, 500)

# After (success case):
assert response.status_code == 200
# or (error case):
assert response.status_code == 422  # validation error
```

For each tested endpoint, determine what the correct response should be:
- `test_chat_endpoint`: with valid input → 200
- `test_quiz_generate_endpoint`: with valid params → 200
- `test_lesson_plan_endpoint`: with valid params → 200
- `test_diagram_validate_endpoint`: with valid params → 200
- etc.

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "fix: assert specific status codes instead of accepting 500"
```

---

### Task 2: Remove empty test file and implement stubs

**Files:**
- Remove: `tests/test_forecasting.py`
- Modify: `tests/test_auth.py`

- [ ] **Step 1: Delete empty test file**

```bash
rm tests/test_forecasting.py
```

- [ ] **Step 2: Implement stub tests in test_auth.py**

```python
# Replace stubs in test_auth.py:

def test_otp_verify_rejects_missing_otp():
    """Verify that /auth/verify-otp returns 401 when no OTP was requested."""
    import httpx
    import pytest

    with pytest.raises(Exception):
        # This should fail validation or auth depending on how the test client is set up
        pass
    # TODO: implement with real test client when available
    assert True


def test_otp_request_rejects_unknown_telegram_id():
    """Verify that /auth/request-otp returns 404 for unknown telegram_id."""
    # TODO: implement with real test client when available
    assert True
```

Replace with actual assertions using the `client` fixture from `conftest.py`:

```python
@pytest.mark.asyncio
async def test_otp_request_rejects_unknown_telegram_id(client):
    response = await client.post("/auth/request-otp", json={"telegram_id": 99999999})
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
```

- [ ] **Step 3: Commit**

```bash
git rm tests/test_forecasting.py
git add tests/test_auth.py
git commit -m "fix: remove empty test file, implement auth stubs"
```

---

### Task 3: Add coverage config and restore CI test suite

**Files:**
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add pytest-cov configuration to pyproject.toml**

```toml
[tool.coverage.run]
source = ["src"]
omit = ["src/agents/*", "src/ingestion/*", "src/notifications/templates/*"]
concurrency = ["asyncio"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise SystemExit",
    "if __name__ == .__main__.:",
]
fail_under = 50
```

- [ ] **Step 2: Restore CI test run**

Edit `.github/workflows/ci.yml` to replace the 22-file ignore list with marker-based filtering:

```yaml
  test:
    runs-on: ubuntu-latest
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv
      - run: uv pip install --system -r requirements.txt
      - run: uv pip install --system -r requirements-bot.txt
      - run: uv pip install --system pytest-timeout pytest-cov
      - name: Run tests (unit + integration, exclude slow)
        run: pytest tests/ -v --no-header --timeout=120 --cov=src --cov-report=term-missing -m "not slow" --tb=short
      - name: Run smoke tests
        run: pytest tests/ -v -m smoke --tb=short
```

- [ ] **Step 3: Add slow marker to pyproject.toml**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
markers = [
    "smoke: quick smoke-test scenarios",
    "integration: integration and journey tests",
    "slow: tests requiring external services (Ollama, etc.) - excluded from CI",
]
```

- [ ] **Step 4: Add slow marker to Ollama-dependent tests**

Add `@pytest.mark.slow` to any test that requires a running Ollama instance (e.g., `test_ollama_provider.py`, integration tests).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .github/workflows/ci.yml
git commit -m "ci: restore full test suite with coverage and tiered markers"
```

---

### Task 4: Enable stricter linting

**Files:**
- Modify: `pyproject.toml` (ruff + mypy sections)
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Enable additional ruff rules**

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C4", "PT", "S"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["E501", "N803", "N806", "S101", "S311"]
"alembic/*" = ["E501"]
```

- [ ] **Step 2: Harden mypy config**

```toml
[tool.mypy]
python_version = "3.12"
strict = false
ignore_missing_imports = true
disable_error_code = [
    "misc",
    "union-attr",
    "attr-defined",
    "valid-type",
    "var-annotated",
    "dict-item",
    "assignment",
]
```

Remove `call-arg`, `arg-type`, and `return-value` from the disabled list (these were previously disabled but should now be enforced).

- [ ] **Step 3: Create pre-commit config**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .pre-commit-config.yaml
git commit -m "lint: enable stricter ruff rules and mypy, add pre-commit hooks"
```

---

### Task 5: Add security scanning to CI

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add pip-audit and bandit jobs**

```yaml
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install uv
      - run: uv pip install --system -r requirements.txt
      - run: uv pip install --system pip-audit bandit
      - name: pip-audit
        run: pip-audit --ignore-vuln PYSEC-2023-123 --ignore-vuln PYSEC-2024-456
        continue-on-error: true
      - name: bandit
        run: bandit -r src/ -c pyproject.toml
        continue-on-error: true
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add pip-audit and bandit security scanning"
```
