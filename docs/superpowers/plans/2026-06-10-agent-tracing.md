# Agent Tracing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist Agentic RAG pipeline traces to PostgreSQL and expose them via REST API.

**Architecture:** PipelineMonitor (in-memory, unchanged for real-time) gets an optional `on_complete` callback that saves completed traces to PostgreSQL via TraceRepository. Three REST endpoints at `/traces` list/detail/delete traces.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL (JSONB), Pydantic, structlog

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/core/tracing/__init__.py` | Package init, exports `TraceRepository` |
| Create | `src/core/tracing/trace_repository.py` | Async CRUD over `agent_traces` table |
| Create | `src/schemas/tracing.py` | Pydantic request/response models |
| Create | `src/api/tracing.py` | FastAPI router with 3 endpoints |
| Create | `tests/test_trace_repository.py` | Unit tests for TraceRepository |
| Create | `tests/test_tracing_api.py` | Integration tests for API |
| Modify | `src/database/models.py` | Add `AgentTrace` SQLAlchemy model |
| Modify | `src/core/monitoring.py` | Add `on_complete` callback + `finalize_trace` |
| Modify | `src/graph/orchestrator.py` | Call `finalize_trace` instead of raw `finish()`+`log_trace()` |
| Modify | `src/main.py` | Wire callback + register router |

---

### Task 1: AgentTrace ORM Model

**Files:**
- Modify: `src/database/models.py` (append before EOF)

- [ ] **Step 1: Add AgentTrace model**

Append to `src/database/models.py`:

```python
class AgentTrace(Base):
    __tablename__ = "agent_traces"

    trace_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    error: Mapped[str] = mapped_column(Text, nullable=True)
    user_message: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text, nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(String(8), nullable=True)
    intent: Mapped[str] = mapped_column(String(64), nullable=True)
    nodes_visited: Mapped[dict] = mapped_column(JSON, default=list)
    node_timings: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
```

- [ ] **Step 2: Verify no syntax errors**

Run: `.venv/bin/python -c "from src.database.models import AgentTrace; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/database/models.py
git commit -m "feat(tracing): add AgentTrace ORM model"
```

---

### Task 2: TraceRepository

**Files:**
- Create: `src/core/tracing/__init__.py`
- Create: `src/core/tracing/trace_repository.py`

- [ ] **Step 1: Create package init**

`src/core/tracing/__init__.py`:
```python
from src.core.tracing.trace_repository import TraceRepository

__all__ = ["TraceRepository"]
```

- [ ] **Step 2: Write failing test**

`tests/test_trace_repository.py`:
```python
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.tracing import TraceRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    return TraceRepository(lambda: mock_session)


@pytest.mark.asyncio
async def test_save_and_get_trace(repo, mock_session):
    from sqlalchemy import select
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(
        trace_id="trace_test",
        start_time=datetime.now(timezone.utc),
        end_time=None,
        status="running",
        error=None,
        user_message="test query",
        response=None,
        user_id=None,
        grade_level=8,
        language="en",
        intent="tutor",
        nodes_visited=["orchestrator"],
        node_timings={},
        metadata={},
        duration_ms=0.0,
    )
    mock_session.execute.return_value = mock_result

    trace = await repo.get_trace("trace_test")
    assert trace is not None
    assert trace["trace_id"] == "trace_test"
    assert trace["status"] == "running"


@pytest.mark.asyncio
async def test_save_trace(repo, mock_session):
    from datetime import datetime, timezone

    await repo.save_trace(
        trace_id="trace_new",
        start_time=datetime.now(timezone.utc),
        status="completed",
        user_message="hello",
        response="world",
        grade_level=10,
        language="en",
        intent="quiz",
        nodes_visited=["orchestrator", "tutor"],
        node_timings={"orchestrator": 100.0, "tutor": 500.0},
        metadata={"hallucination_rate": 0.0},
        duration_ms=600.0,
    )
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_traces_with_filters(repo, mock_session):
    from sqlalchemy import select, func
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(
            trace_id="t1", start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc), status="completed",
            error=None, user_message="q1", response="a1",
            user_id=None, grade_level=8, language="en", intent="tutor",
            nodes_visited=[], node_timings={}, metadata={}, duration_ms=100.0,
        ),
    ]
    mock_session.execute.return_value = mock_result

    results, total = await repo.list_traces(status="completed", limit=10)
    assert len(results) == 1
    assert results[0]["trace_id"] == "t1"


@pytest.mark.asyncio
async def test_delete_trace(repo, mock_session):
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(trace_id="t_del")
    mock_session.execute.return_value = mock_result

    deleted = await repo.delete_trace("t_del")
    assert deleted is True
    mock_session.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_nonexistent_trace(repo, mock_session):
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    deleted = await repo.delete_trace("nonexistent")
    assert deleted is False
    mock_session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_old_traces(repo, mock_session):
    import uuid
    mock_result = AsyncMock()
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(trace_id="old1"),
        MagicMock(trace_id="old2"),
    ]
    mock_session.execute.return_value = mock_result

    count = await repo.cleanup_old(max_age_days=1)
    assert count == 2
    assert mock_session.delete.await_count == 2
    mock_session.flush.assert_awaited()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_trace_repository.py -v --tb=short`
Expected: ModuleNotFoundError or ImportError (TraceRepository not imported yet)

- [ ] **Step 4: Write TraceRepository**

`src/core/tracing/trace_repository.py`:
```python
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AgentTrace

logger = structlog.get_logger()


class TraceRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def _get_session(self) -> AsyncSession:
        return self._session_factory()

    async def save_trace(
        self,
        trace_id: str,
        start_time: datetime,
        status: str,
        user_message: str,
        response: Optional[str] = None,
        end_time: Optional[datetime] = None,
        error: Optional[str] = None,
        user_id: Optional[UUID] = None,
        grade_level: Optional[int] = None,
        language: Optional[str] = None,
        intent: Optional[str] = None,
        nodes_visited: Optional[list] = None,
        node_timings: Optional[dict] = None,
        metadata: Optional[dict] = None,
        duration_ms: float = 0.0,
    ) -> None:
        session = await self._get_session()
        try:
            trace = AgentTrace(
                trace_id=trace_id,
                start_time=start_time,
                end_time=end_time,
                status=status,
                error=error,
                user_message=user_message,
                response=response,
                user_id=user_id,
                grade_level=grade_level,
                language=language,
                intent=intent,
                nodes_visited=nodes_visited or [],
                node_timings=node_timings or {},
                metadata=metadata or {},
                duration_ms=duration_ms,
            )
            session.add(trace)
            await session.flush()
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("save_trace_failed", trace_id=trace_id)
        finally:
            await session.close()

    async def get_trace(self, trace_id: str) -> Optional[dict]:
        session = await self._get_session()
        try:
            result = await session.execute(
                select(AgentTrace).where(AgentTrace.trace_id == trace_id)
            )
            trace = result.scalar_one_or_none()
            if trace is None:
                return None
            return self._to_dict(trace)
        finally:
            await session.close()

    async def list_traces(
        self,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        intent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        session = await self._get_session()
        try:
            query = select(AgentTrace)
            count_query = select(func.count(AgentTrace.trace_id))

            if status:
                query = query.where(AgentTrace.status == status)
                count_query = count_query.where(AgentTrace.status == status)
            if user_id:
                query = query.where(AgentTrace.user_id == user_id)
                count_query = count_query.where(AgentTrace.user_id == user_id)
            if date_from:
                query = query.where(AgentTrace.start_time >= date_from)
                count_query = count_query.where(AgentTrace.start_time >= date_from)
            if date_to:
                query = query.where(AgentTrace.start_time <= date_to)
                count_query = count_query.where(AgentTrace.start_time <= date_to)
            if intent:
                query = query.where(AgentTrace.intent == intent)
                count_query = count_query.where(AgentTrace.intent == intent)

            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0

            query = query.order_by(AgentTrace.start_time.desc())
            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            traces = result.scalars().all()

            return [self._to_dict(t) for t in traces], total
        finally:
            await session.close()

    async def delete_trace(self, trace_id: str) -> bool:
        session = await self._get_session()
        try:
            result = await session.execute(
                select(AgentTrace).where(AgentTrace.trace_id == trace_id)
            )
            trace = result.scalar_one_or_none()
            if trace is None:
                return False
            await session.delete(trace)
            await session.flush()
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            logger.exception("delete_trace_failed", trace_id=trace_id)
            return False
        finally:
            await session.close()

    async def cleanup_old(self, max_age_days: int = 30) -> int:
        session = await self._get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            result = await session.execute(
                select(AgentTrace).where(AgentTrace.start_time < cutoff)
            )
            old_traces = result.scalars().all()
            count = len(old_traces)
            for t in old_traces:
                await session.delete(t)
            await session.flush()
            await session.commit()
            logger.info("cleanup_old_traces", count=count, max_age_days=max_age_days)
            return count
        except Exception:
            await session.rollback()
            logger.exception("cleanup_traces_failed")
            return 0
        finally:
            await session.close()

    @staticmethod
    def _to_dict(trace: AgentTrace) -> dict:
        return {
            "trace_id": trace.trace_id,
            "start_time": trace.start_time.isoformat() if trace.start_time else None,
            "end_time": trace.end_time.isoformat() if trace.end_time else None,
            "status": trace.status,
            "error": trace.error,
            "user_message": trace.user_message,
            "response": trace.response,
            "user_id": str(trace.user_id) if trace.user_id else None,
            "grade_level": trace.grade_level,
            "language": trace.language,
            "intent": trace.intent,
            "nodes_visited": trace.nodes_visited,
            "node_timings": trace.node_timings,
            "metadata": trace.metadata,
            "duration_ms": trace.duration_ms,
        }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_trace_repository.py -v --tb=short`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/core/tracing/ tests/test_trace_repository.py
git commit -m "feat(tracing): add TraceRepository with async CRUD"
```

---

### Task 3: Tracing Schemas

**Files:**
- Create: `src/schemas/tracing.py`

- [ ] **Step 1: Create schema file**

`src/schemas/tracing.py`:
```python
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.schemas.base import SchemaModel


class TraceResponse(SchemaModel):
    trace_id: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str
    error: Optional[str] = None
    user_message: str = ""
    response: Optional[str] = None
    user_id: Optional[str] = None
    grade_level: Optional[int] = None
    language: Optional[str] = None
    intent: Optional[str] = None
    nodes_visited: list = []
    node_timings: dict = {}
    metadata: dict = {}
    duration_ms: float = 0.0


class TraceListResponse(SchemaModel):
    traces: list[TraceResponse]
    total: int
    limit: int
    offset: int


class TraceDeleteResponse(SchemaModel):
    deleted: bool
    trace_id: str
```

- [ ] **Step 2: Verify imports**

Run: `.venv/bin/python -c "from src.schemas.tracing import TraceResponse, TraceListResponse, TraceDeleteResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/schemas/tracing.py
git commit -m "feat(tracing): add API schemas for trace endpoints"
```

---

### Task 4: Tracing API Router

**Files:**
- Create: `src/api/tracing.py`

- [ ] **Step 1: Write failing test**

`tests/test_tracing_api.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_trace.return_value = {
        "trace_id": "trace_test",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": None,
        "status": "completed",
        "error": None,
        "user_message": "hello",
        "response": "world",
        "user_id": None,
        "grade_level": 8,
        "language": "en",
        "intent": "tutor",
        "nodes_visited": ["orchestrator"],
        "node_timings": {},
        "metadata": {},
        "duration_ms": 100.0,
    }
    repo.list_traces.return_value = ([], 0)
    repo.delete_trace.return_value = True
    return repo


@pytest.mark.asyncio
async def test_get_trace_detail(mock_repo):
    with patch("src.api.tracing.TraceRepository", return_value=mock_repo):
        from src.api.tracing import router
        from fastapi.testclient import TestClient
        from src.main import app

        client = TestClient(app)
        response = client.get("/traces/trace_test")
        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == "trace_test"


@pytest.mark.asyncio
async def test_get_nonexistent_trace(mock_repo):
    mock_repo.get_trace.return_value = None
    with patch("src.api.tracing.TraceRepository", return_value=mock_repo):
        from fastapi.testclient import TestClient
        from src.main import app

        client = TestClient(app)
        response = client.get("/traces/nonexistent")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_traces(mock_repo):
    mock_repo.list_traces.return_value = ([], 0)
    with patch("src.api.tracing.TraceRepository", return_value=mock_repo):
        from fastapi.testclient import TestClient
        from src.main import app

        client = TestClient(app)
        response = client.get("/traces")
        assert response.status_code == 200
        data = response.json()
        assert "traces" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_delete_trace(mock_repo):
    with patch("src.api.tracing.TraceRepository", return_value=mock_repo):
        from fastapi.testclient import TestClient
        from src.main import app

        client = TestClient(app)
        response = client.delete("/traces/trace_test")
        assert response.status_code == 200
        assert response.json()["deleted"] is True
```

- [ ] **Step 2: Create API router**

`src/api/tracing.py`:
```python
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from src.database.session import async_session_factory
from src.core.tracing import TraceRepository
from src.schemas.tracing import TraceDeleteResponse, TraceListResponse, TraceResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/traces", tags=["Tracing"])


def get_trace_repository() -> TraceRepository:
    return TraceRepository(async_session_factory)


@router.get("", response_model=TraceListResponse)
async def list_traces(
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[UUID] = Query(None, description="Filter by user UUID"),
    intent: Optional[str] = Query(None, description="Filter by intent"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: TraceRepository = Depends(get_trace_repository),
):
    try:
        traces, total = await repo.list_traces(
            status=status,
            user_id=user_id,
            intent=intent,
            limit=limit,
            offset=offset,
        )
        return TraceListResponse(
            traces=[TraceResponse(**t) for t in traces],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error("list_traces_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    repo: TraceRepository = Depends(get_trace_repository),
):
    try:
        trace = await repo.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return TraceResponse(**trace)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_trace_error", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{trace_id}", response_model=TraceDeleteResponse)
async def delete_trace(
    trace_id: str,
    repo: TraceRepository = Depends(get_trace_repository),
):
    try:
        deleted = await repo.delete_trace(trace_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Trace not found")
        return TraceDeleteResponse(deleted=True, trace_id=trace_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_trace_error", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 3: Commit**

```bash
git add src/api/tracing.py tests/test_tracing_api.py
git commit -m "feat(tracing): add REST API router for traces"
```

---

### Task 5: Wire PipelineMonitor Callback

**Files:**
- Modify: `src/core/monitoring.py`

- [ ] **Step 1: Add on_complete callback to PipelineMonitor**

In `src/core/monitoring.py`, modify `PipelineMonitor.__init__`:

```python
class PipelineMonitor:
    def __init__(self):
        self.traces: dict[str, PipelineTrace] = {}
        self._on_complete: Optional[callable] = None
```

Add methods:

```python
    def set_on_complete(self, callback: callable) -> None:
        """Set a callback invoked when a trace completes.

        Callback signature: callback(trace: PipelineTrace) -> None
        For async callbacks, use asyncio.create_task() inside the callback.
        """
        self._on_complete = callback

    async def finalize_trace(
        self, trace_id: str, status: str, metadata: Optional[dict] = None,
    ) -> None:
        """Finalize a trace, update metadata, log it, and fire on_complete."""
        trace = self.traces.get(trace_id)
        if not trace:
            return
        if metadata:
            trace.metadata.update(metadata)
        trace.finish(status=status)
        self.log_trace(trace)
        if self._on_complete:
            self._on_complete(trace)
```

Add import for `Optional` if not already present (it is — check line 16 of monitoring.py: `from typing import Optional`).

- [ ] **Step 2: Update existing tests or run manually**

Run: `.venv/bin/python -m pytest tests/test_monitoring.py -v --tb=short 2>&1 || echo "No existing monitoring tests"`

- [ ] **Step 3: Commit**

```bash
git add src/core/monitoring.py
git commit -m "feat(tracing): add on_complete callback to PipelineMonitor"
```

---

### Task 6: Wire Tracing into Graph Orchestrator

**Files:**
- Modify: `src/graph/orchestrator.py`

- [ ] **Step 1: Replace trace finalization in run_graph**

In `src/graph/orchestrator.py`, replace the try/except/finally block at ~line 183-200:

Current code:
```python
    try:
        result = await graph.ainvoke(initial_state, config)
        trace.finish(status="completed")
        # Populate trace metadata with 5 key metrics
        trace.metadata.update({
            "retrieval_iterations": result.get("retrieval_iterations", 0),
            "coverage_score": result.get("coverage_score", 0.0),
            "groundedness": result.get("groundedness_score", 0.0),
            "hallucination_rate": result.get("hallucination_rate", 0.0),
            "verdict": result.get("safety_action", ""),
            "requires_teacher_review": result.get("requires_teacher_review", False),
            "evidence_count": len(result.get("evidence_ids", [])),
        })
    except Exception as e:
        trace.finish(status="failed", error=str(e))
        raise
    finally:
        pipeline_monitor.log_trace(trace)
        await router.close()
```

Replace with:
```python
    try:
        result = await graph.ainvoke(initial_state, config)
        metadata = {
            "user_message": initial_state.user_message,
            "response": result.get("draft", ""),
            "retrieval_iterations": result.get("retrieval_iterations", 0),
            "coverage_score": result.get("coverage_score", 0.0),
            "groundedness": result.get("groundedness_score", 0.0),
            "hallucination_rate": result.get("hallucination_rate", 0.0),
            "verdict": result.get("safety_action", ""),
            "requires_teacher_review": result.get("requires_teacher_review", False),
            "evidence_count": len(result.get("evidence_ids", [])),
        }
        await pipeline_monitor.finalize_trace(
            trace.trace_id, "completed", metadata=metadata,
        )
    except Exception as e:
        await pipeline_monitor.finalize_trace(
            trace.trace_id, "failed",
            metadata={"user_message": initial_state.user_message, "error": str(e)},
        )
        raise
    finally:
        await router.close()
```

Also update the import to make sure `pipeline_monitor` is imported (it already is at line 18 of orchestrator.py).

- [ ] **Step 2: Verify syntax**

Run: `.venv/bin/python -c "from src.graph.orchestrator import run_graph; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/graph/orchestrator.py
git commit -m "feat(tracing): wire finalize_trace into graph orchestrator"
```

---

### Task 7: Wire Everything Together in main.py

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Add trace repository wiring to main.py**

Add import near the other `from src.api` imports:
```python
from src.api.tracing import router as tracing_router
```

Add import for TraceRepository near the other core imports:
```python
from src.core.tracing import TraceRepository
from src.core.monitoring import pipeline_monitor
```

Add the wiring inside the `lifespan` context manager, after `await init_db()`:
```python
    # Wire trace persistence
    repo = TraceRepository(async_session_factory)
    pipeline_monitor.set_on_complete(
        lambda trace: asyncio.create_task(
            _save_trace_from_pipeline(trace, repo)
        )
    )
```

Add the helper function near the top of main.py (before `lifespan`):
```python
async def _save_trace_from_pipeline(
    trace: "PipelineTrace", repo: "TraceRepository",
) -> None:
    """Save a completed PipelineTrace to persistent storage."""
    try:
        await repo.save_trace(
            trace_id=trace.trace_id,
            start_time=datetime.fromtimestamp(trace.start_time, tz=timezone.utc),
            status=trace.status,
            user_message=trace.metadata.get("user_message", ""),
            response=trace.metadata.get("response"),
            end_time=datetime.fromtimestamp(trace.end_time, tz=timezone.utc) if trace.end_time else None,
            error=trace.error,
            nodes_visited=trace.nodes_visited,
            node_timings={
                k: v for k, v in trace.node_timings.items()
                if not k.endswith("_start")
            },
            metadata={k: v for k, v in trace.metadata.items()
                      if k not in ("user_message", "response")},
            duration_ms=trace.duration_ms,
        )
    except Exception:
        logger.exception("trace_persist_failed", trace_id=trace.trace_id)
```

Add `from datetime import datetime, timezone` to main.py imports.

Add `import asyncio` to main.py imports.

Add `from src.core.tracing import TraceRepository` (if not already added above).

Register the router after all existing `include_router` calls:
```python
app.include_router(tracing_router)
```

- [ ] **Step 2: Verify syntax**

Run: `.venv/bin/python -c "from src.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat(tracing): wire trace persistence and register tracing API router"
```

---

### Task 8: Final Verification

- [ ] **Step 1: Run all tracing tests**

Run: `.venv/bin/python -m pytest tests/test_trace_repository.py tests/test_tracing_api.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Lint check**

Run: `.venv/bin/ruff check src/core/tracing/ src/api/tracing.py src/schemas/tracing.py src/database/models.py src/core/monitoring.py src/graph/orchestrator.py src/main.py`
Expected: No errors

- [ ] **Step 3: Verify the full app starts**

```bash
.venv/bin/python -c "
from src.main import app
from src.core.tracing import TraceRepository
from src.core.monitoring import pipeline_monitor
print('Imports OK')
# Verify router registered
routes = [r.path for r in app.routes]
assert '/traces' in ''.join(routes), 'Traces router not registered'
print('Router registered OK')
# Verify callback set
assert pipeline_monitor._on_complete is not None, 'Callback not set'
print('Callback wired OK')
"
```
Expected: All three lines printed

- [ ] **Step 4: Final commit**

```bash
git add -A && git commit -m "chore: final verification for agent tracing (PRD-009 sub-project 3)"
```
