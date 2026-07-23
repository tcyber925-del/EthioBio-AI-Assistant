# Track 3 — Performance & Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate ChromaDB async blocking, add LLM circuit breaker, fix eval task leak, move secrets to env vars, pin Ollama version.

**Architecture:** Switch to pgvector-only vector store. Circuit breaker pattern per LLM provider. Semaphore-limited eval tasks. Docker secrets via env variables.

**Tech Stack:** pgvector, FastAPI, Redis, Docker, httpx

---

### Task 1: Remove ChromaDB, make pgvector the sole vector store

**Files:**
- Modify: `src/rag/vector_store.py`
- Modify: `src/rag/pgvector_store.py`
- Modify: `src/config.py`
- Remove: `chromadb` from `requirements.txt`

- [ ] **Step 1: Update config to remove chroma option**

```python
# In src/config.py
# Remove: store_backend: str = "chroma"  # "chroma" or "pgvector"
# Replace with:
store_backend: str = "pgvector"  # always pgvector
```

- [ ] **Step 2: Simplify vector_store.py**

```python
# src/rag/vector_store.py — remove ChromaDB, delegate to pgvector only

import structlog
from src.config import settings

logger = structlog.get_logger()


class VectorStore:
    def __init__(self, persist_directory: str = "", collection_name: str = ""):
        self._pgvector = self._init_pgvector()

    def _init_pgvector(self):
        from src.rag.pgvector_store import PgVectorStore
        return PgVectorStore()

    async def add_embedding(self, *args, **kwargs):
        return await self._pgvector.add_embedding(*args, **kwargs)

    async def query(self, *args, **kwargs):
        return await self._pgvector.query(*args, **kwargs)

    async def delete_embedding(self, *args, **kwargs):
        return await self._pgvector.delete_embedding(*args, **kwargs)

    async def collection_stats(self, *args, **kwargs):
        return await self._pgvector.collection_stats(*args, **kwargs)
```

- [ ] **Step 3: Remove chromadb from requirements.txt**

Delete the `chromadb` line from `requirements.txt`.

- [ ] **Step 4: Commit**

```bash
git add src/rag/vector_store.py src/config.py requirements.txt
git commit -m "perf: remove ChromaDB, make pgvector sole vector store"
```

---

### Task 2: Add LLM circuit breaker

**Files:**
- Create: `src/llm/circuit_breaker.py`
- Modify: `src/llm/manager.py`
- Modify: `src/observability/health.py`

- [ ] **Step 1: Write circuit breaker**

```python
# src/llm/circuit_breaker.py
import time
import structlog

logger = structlog.get_logger()


class CircuitState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, name: str, threshold: int = 5, recovery_timeout: float = 30.0, half_open_max: int = 3):
        self.name = name
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_successes = 0

    @property
    def is_available(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_successes = 0
                logger.info("circuit_breaker_half_open", provider=self.name)
                return True
            return False
        return True  # HALF_OPEN — allow one request

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.half_open_max:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("circuit_breaker_closed", provider=self.name)
        else:
            self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.threshold:
            self.state = CircuitState.OPEN
            logger.warning("circuit_breaker_opened", provider=self.name, failures=self.failure_count)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "is_available": self.is_available,
        }
```

- [ ] **Step 2: Integrate into ProviderManager**

```python
# In src/llm/manager.py, add to __init__:
from src.llm.circuit_breaker import CircuitBreaker

self.breakers: dict[str, CircuitBreaker] = {
    "ollama": CircuitBreaker("ollama"),
    "openrouter": CircuitBreaker("openrouter"),
    "openai": CircuitBreaker("openai"),
    "anthropic": CircuitBreaker("anthropic"),
}
```

In `route()` and `route_stream()`, check breaker before calling:

```python
async def route(self, prompt: str, system_prompt: str = "", **kwargs):
    for name, provider in self.providers:
        breaker = self.breakers.get(name)
        if breaker and not breaker.is_available:
            logger.info("provider_skipped_circuit_open", provider=name)
            continue
        try:
            result = await provider.chat(prompt, system_prompt, **kwargs)
            if breaker:
                breaker.record_success()
            return result
        except Exception as e:
            if breaker:
                breaker.record_failure()
            logger.warning("provider_failed", provider=name, error=str(e)[:200])
            continue
    raise RuntimeError("All providers failed")
```

- [ ] **Step 3: Add breaker health to /health/modules**

```python
# In the health endpoint or registry, expose circuit breaker states
from src.llm.manager import ProviderManager

async def get_circuit_breaker_health():
    manager = ProviderManager()
    return {name: breaker.to_dict() for name, breaker in manager.breakers.items()}
```

- [ ] **Step 4: Commit**

```bash
git add src/llm/circuit_breaker.py src/llm/manager.py
git commit -m "feat: add LLM circuit breaker with per-provider state"
```

---

### Task 3: Fix unbounded eval tasks with semaphore

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Add semaphore and trace store eviction**

```python
# In src/main.py, add near the top of lifespan:
_eval_semaphore = asyncio.Semaphore(5)


async def _evaluate_trace(trace):
    async with _eval_semaphore:
        # existing _evaluate_trace logic...
        pass


async def _on_trace_complete(trace):
    await _save_trace_from_pipeline(trace, repo)
    asyncio.create_task(_evaluate_trace(trace))
```

And in `pipeline_monitor.set_on_complete`, ensure the callback is fire-and-forget wrapped:

```python
pipeline_monitor.set_on_complete(
    lambda trace: asyncio.create_task(_evaluate_trace(trace))
)
```

- [ ] **Step 2: Add trace store LRU eviction**

In `src/core/monitoring.py`, add a max size to `pipeline_monitor`:

```python
# In PipelineMonitor class
MAX_TRACES = 1000

def _add_trace(self, trace):
    self.traces[trace.trace_id] = trace
    if len(self.traces) > self.MAX_TRACES:
        # Remove oldest by sorting by start_time
        oldest = sorted(self.traces.values(), key=lambda t: t.start_time)[0]
        self.traces.pop(oldest.trace_id, None)
```

- [ ] **Step 3: Commit**

```bash
git add src/main.py src/core/monitoring.py
git commit -m "perf: limit eval tasks to 5 concurrent, add trace store LRU eviction"
```

---

### Task 4: Move Docker secrets to env vars

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`

- [ ] **Step 1: Update docker-compose.yml**

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${PG_USER:-ethiobio}
      POSTGRES_PASSWORD: ${PG_PASSWORD}
      POSTGRES_DB: ${PG_DB:-ethiobio}

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
```

- [ ] **Step 2: Add new vars to .env.example**

```bash
# PostgreSQL
PG_PASSWORD=change-me-pg-password
PG_USER=ethiobio
PG_DB=ethiobio

# Grafana
GRAFANA_PASSWORD=change-me-grafana-password
GRAFANA_USER=admin

# Ollama version
OLLAMA_VERSION=0.5.12
```

- [ ] **Step 3: Pin Ollama version**

```yaml
services:
  ollama:
    image: ollama/ollama:${OLLAMA_VERSION:-0.5.12}
```

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "infra: move docker secrets to env vars, pin ollama version"
```
