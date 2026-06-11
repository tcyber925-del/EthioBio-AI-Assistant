# Governance Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an admin dashboard page for reviewing pipeline responses flagged by the Safety Node.

**Architecture:** Two endpoints on the existing `/admin` router to list and resolve flagged traces. Review state stored in `agent_traces.event_metadata` JSONB. Frontend is a new `/admin/review` Next.js page with list + detail views.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL JSONB, Next.js (client components), TailwindCSS, fetchWithAuth

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `src/api/admin.py` | Add `GET /admin/review` + `PATCH /admin/review/{trace_id}` |
| Create | `tests/test_admin_review.py` | Backend tests for review endpoints |
| Create | `dashboard/src/app/admin/review/page.tsx` | Main review page: list + detail |
| Create | `dashboard/src/components/governance/ReviewQueue.tsx` | List table component |
| Create | `dashboard/src/components/governance/ReviewDetail.tsx` | Expandable detail row |
| Create | `dashboard/src/components/governance/ReviewNotesModal.tsx` | Resolve modal with notes |
| Modify | `dashboard/src/app/admin/layout.tsx` | Add "Review Queue" nav item |

Note: `dashboard/next.config.js` already has `/admin/:path*` rewrite — no change needed.

---

### Task 1: Backend Review API Endpoints

**Files:**
- Modify: `src/api/admin.py` (append new schemas + endpoints)
- Create: `tests/test_admin_review.py`

- [ ] **Step 1: Write failing tests**

`tests/test_admin_review.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _make_trace_metadata(**overrides) -> dict:
    return {
        "requires_teacher_review": True,
        "safety_issues": ["profanity"],
        "safety_action": "revise",
        "user_message": "test query",
        "response": "test response",
        "intent": "tutor",
        "grade_level": 8,
        "language": "en",
        "groundedness_score": 0.3,
        "hallucination_rate": 0.15,
        **overrides,
    }


@pytest.fixture
def client():
    with patch("src.api.admin.get_session") as mock_get_session, \
         patch("src.api.admin.require_admin") as mock_admin:
        mock_admin.return_value = MagicMock()
        from src.main import app
        yield TestClient(app)


@pytest.mark.asyncio
async def test_list_pending_reviews(client):
    """GET /admin/review should return flagged traces with status=pending."""
    response = client.get("/admin/review")
    assert response.status_code == 200
    data = response.json()
    assert "traces" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_resolved_reviews(client):
    """GET /admin/review should filter by status=resolved."""
    response = client.get("/admin/review?status=resolved")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_resolve_trace(client):
    """PATCH /admin/review/{trace_id} should mark trace as resolved."""
    response = client.patch(
        "/admin/review/trace_test",
        json={"action": "resolve", "review_notes": "Looks good"},
    )
    assert response.status_code in (200, 404)  # 404 if trace doesn't exist


@pytest.mark.asyncio
async def test_resolve_nonexistent_trace(client):
    """PATCH /admin/review/nonexistent should return 404."""
    response = client.patch(
        "/admin/review/nonexistent",
        json={"action": "resolve"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_resolve_without_admin(client):
    """Unauthenticated request should return 401/403."""
    with patch("src.api.admin.require_admin", side_effect=HTTPException(403)):
        response = client.get("/admin/review")
        assert response.status_code == 403
```

Run: `.venv/bin/python -m pytest tests/test_admin_review.py -v --tb=short`
Expected: FAIL (ModuleNotFoundError or ImportError since admin.py doesn't have these endpoints yet)

- [ ] **Step 2: Add schemas and endpoints to admin.py**

Add to the top of `src/api/admin.py` (after existing imports):
```python
from datetime import datetime, timezone
from src.database.models import AgentTrace
```

Add Pydantic schemas after the existing `UpdateUserRoleRequest` class:
```python
class ReviewListResponse(SchemaModel):
    traces: list[dict]
    total: int
    limit: int
    offset: int


class ReviewActionRequest(SchemaModel):
    action: str = "resolve"
    review_notes: str = ""


class ReviewActionResponse(SchemaModel):
    trace_id: str
    status: str
    reviewed_at: str
```

Add endpoints at the end of the file (before the `def run()` or any CLI block):

```python
@router.get("/review", response_model=ReviewListResponse)
async def list_review_items(
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    try:
        query = select(AgentTrace).where(
            AgentTrace.event_metadata["requires_teacher_review"].as_string() == "true"
        )
        count_query = select(func.count(AgentTrace.trace_id)).where(
            AgentTrace.event_metadata["requires_teacher_review"].as_string() == "true"
        )

        if status == "resolved":
            query = query.where(
                AgentTrace.event_metadata["reviewed"].as_string() == "true"
            )
            count_query = count_query.where(
                AgentTrace.event_metadata["reviewed"].as_string() == "true"
            )
        else:
            query = query.where(
                (AgentTrace.event_metadata["reviewed"].as_string() == "false")
                | (AgentTrace.event_metadata["reviewed"].is_(None))
            )
            count_query = count_query.where(
                (AgentTrace.event_metadata["reviewed"].as_string() == "false")
                | (AgentTrace.event_metadata["reviewed"].is_(None))
            )

        count_result = await session.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(AgentTrace.start_time.desc())
        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        traces = result.scalars().all()

        items = []
        for t in traces:
            md = t.event_metadata or {}
            items.append({
                "trace_id": t.trace_id,
                "user_message": t.user_message,
                "response": t.response,
                "intent": t.intent,
                "grade_level": t.grade_level,
                "language": t.language,
                "safety_issues": md.get("safety_issues", []),
                "safety_action": md.get("safety_action", ""),
                "groundedness_score": md.get("groundedness_score", 0.0),
                "hallucination_rate": md.get("hallucination_rate", 0.0),
                "requires_teacher_review": True,
                "reviewed": md.get("reviewed", False),
                "review_notes": md.get("review_notes"),
                "reviewed_at": md.get("reviewed_at"),
                "created_at": t.start_time.isoformat() if t.start_time else None,
            })

        return ReviewListResponse(traces=items, total=total, limit=limit, offset=offset)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("list_review_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/review/{trace_id}", response_model=ReviewActionResponse)
async def resolve_review_item(
    trace_id: str,
    body: ReviewActionRequest,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    try:
        result = await session.execute(
            select(AgentTrace).where(AgentTrace.trace_id == trace_id)
        )
        trace = result.scalar_one_or_none()
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")

        md = dict(trace.event_metadata or {})
        if not md.get("requires_teacher_review"):
            raise HTTPException(
                status_code=400,
                detail="Trace does not require teacher review",
            )

        now = datetime.now(timezone.utc).isoformat()
        md["reviewed"] = True
        md["reviewed_at"] = now
        md["review_notes"] = body.review_notes
        trace.event_metadata = md

        await session.flush()
        await session.commit()

        return ReviewActionResponse(
            trace_id=trace_id,
            status="resolved",
            reviewed_at=now,
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("resolve_review_error", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

Add imports to the top of admin.py:
- Add `from datetime import datetime, timezone`
- Add `from src.database.models import AgentTrace`
- Add `from sqlalchemy import func` (if not already imported)

Check existing imports — admin.py already has: `from sqlalchemy import select`, `from sqlalchemy.ext.asyncio import AsyncSession`, `from src.database.models import User, ModelRoutingLog, ...`. Verify and add `AgentTrace` to the models import.

- [ ] **Step 3: Verify syntax**

Run: `.venv/bin/python -c "from src.api.admin import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_admin_review.py -v --tb=short`
Expected: Tests pass or have manageable failures (mock setup may need adjustment)

- [ ] **Step 5: Run existing admin tests to check no regressions**

Run: `.venv/bin/python -m pytest tests/ -k "admin" -v --tb=short 2>&1 || echo "No admin-specific tests"`

- [ ] **Step 6: Commit**

```bash
git add src/api/admin.py tests/test_admin_review.py
git commit -m "feat(governance): add review API endpoints for flagged traces"
```

---

### Task 2: Frontend Review Queue Page

**Files:**
- Create: `dashboard/src/app/admin/review/page.tsx`
- Create: `dashboard/src/components/governance/ReviewQueue.tsx`
- Create: `dashboard/src/components/governance/ReviewDetail.tsx`
- Create: `dashboard/src/components/governance/ReviewNotesModal.tsx`

- [ ] **Step 1: Create ReviewQueue component**

`dashboard/src/components/governance/ReviewQueue.tsx`:
```tsx
'use client'

import { useState } from 'react'
import { AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import ReviewDetail from './ReviewDetail'

interface ReviewItem {
  trace_id: string
  user_message: string
  response: string | null
  intent: string
  grade_level: number | null
  language: string | null
  safety_issues: string[]
  safety_action: string
  groundedness_score: number
  hallucination_rate: number
  requires_teacher_review: boolean
  reviewed: boolean
  review_notes: string | null
  reviewed_at: string | null
  created_at: string | null
}

interface ReviewQueueProps {
  items: ReviewItem[]
  onResolve: (traceId: string, notes: string) => void
  loading: boolean
}

export default function ReviewQueue({ items, onResolve, loading }: ReviewQueueProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (loading) {
    return <div className="text-gray-500">Loading review queue...</div>
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <CheckCircle className="mx-auto h-12 w-12 mb-3" />
        <p className="text-lg">No items pending review</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.trace_id} className="border rounded-lg">
          <button
            onClick={() => setExpandedId(expandedId === item.trace_id ? null : item.trace_id)}
            className="w-full flex items-center justify-between p-4 hover:bg-gray-50 text-left"
          >
            <div className="flex items-center gap-3 min-w-0">
              {item.reviewed ? (
                <CheckCircle className="h-5 w-5 text-green-500 shrink-0" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-500 shrink-0" />
              )}
              <div className="min-w-0">
                <p className="text-sm text-gray-900 truncate max-w-md">
                  {item.user_message}
                </p>
                <p className="text-xs text-gray-500">
                  {item.intent} &middot; Grade {item.grade_level ?? 'N/A'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {item.safety_issues.slice(0, 2).map((issue) => (
                <span key={issue} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                  {issue}
                </span>
              ))}
              {item.reviewed ? (
                <span className="text-xs text-green-600 flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" /> Reviewed
                </span>
              ) : (
                <span className="text-xs text-yellow-600 flex items-center gap-1">
                  <Clock className="h-3 w-3" /> Pending
                </span>
              )}
            </div>
          </button>
          {expandedId === item.trace_id && (
            <ReviewDetail item={item} onResolve={onResolve} />
          )}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Create ReviewDetail component**

`dashboard/src/components/governance/ReviewDetail.tsx`:
```tsx
'use client'

import { useState } from 'react'
import ReviewNotesModal from './ReviewNotesModal'

interface ReviewItem {
  trace_id: string
  user_message: string
  response: string | null
  intent: string
  grade_level: number | null
  language: string | null
  safety_issues: string[]
  safety_action: string
  groundedness_score: number
  hallucination_rate: number
  requires_teacher_review: boolean
  reviewed: boolean
  review_notes: string | null
  reviewed_at: string | null
  created_at: string | null
}

interface ReviewDetailProps {
  item: ReviewItem
  onResolve: (traceId: string, notes: string) => void
}

export default function ReviewDetail({ item, onResolve }: ReviewDetailProps) {
  const [showModal, setShowModal] = useState(false)

  const scoreColor = (score: number) => {
    if (score >= 0.7) return 'text-green-600'
    if (score >= 0.4) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="border-t px-4 py-4 space-y-4 bg-gray-50">
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">User Message</h4>
        <p className="text-sm text-gray-900">{item.user_message}</p>
      </div>

      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Response</h4>
        <p className="text-sm text-gray-900 whitespace-pre-wrap">{item.response ?? '(no response)'}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Safety Issues</h4>
          {item.safety_issues.length > 0 ? (
            <ul className="text-sm text-red-600 list-disc list-inside">
              {item.safety_issues.map((issue) => <li key={issue}>{issue}</li>)}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">None</p>
          )}
        </div>
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Safety Action</h4>
          <p className="text-sm text-gray-900">{item.safety_action || 'N/A'}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Groundedness</h4>
          <p className={`text-sm font-medium ${scoreColor(item.groundedness_score)}`}>
            {(item.groundedness_score * 100).toFixed(0)}%
          </p>
        </div>
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Hallucination Rate</h4>
          <p className={`text-sm font-medium ${scoreColor(1 - item.hallucination_rate)}`}>
            {(item.hallucination_rate * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {item.review_notes && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Review Notes</h4>
          <p className="text-sm text-gray-700 italic">{item.review_notes}</p>
        </div>
      )}

      {!item.reviewed && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            Resolve
          </button>
        </div>
      )}

      {showModal && (
        <ReviewNotesModal
          traceId={item.trace_id}
          onConfirm={(notes) => { onResolve(item.trace_id, notes); setShowModal(false) }}
          onCancel={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 3: Create ReviewNotesModal component**

`dashboard/src/components/governance/ReviewNotesModal.tsx`:
```tsx
'use client'

import { useState } from 'react'

interface ReviewNotesModalProps {
  traceId: string
  onConfirm: (notes: string) => void
  onCancel: () => void
}

export default function ReviewNotesModal({ traceId, onConfirm, onCancel }: ReviewNotesModalProps) {
  const [notes, setNotes] = useState('')

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
        <h3 className="text-lg font-semibold mb-2">Resolve Review Item</h3>
        <p className="text-sm text-gray-500 mb-4">Trace: {traceId}</p>

        <label className="block text-sm font-medium text-gray-700 mb-1">
          Review Notes (optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add notes about your review..."
          className="w-full border rounded-lg p-3 text-sm h-24 resize-none"
        />

        <div className="flex justify-end gap-3 mt-4">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(notes)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            Confirm & Resolve
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create the review page**

`dashboard/src/app/admin/review/page.tsx`:
```tsx
'use client'

import { useEffect, useState, useCallback } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import ReviewQueue from '@/components/governance/ReviewQueue'

interface ReviewItem {
  trace_id: string
  user_message: string
  response: string | null
  intent: string
  grade_level: number | null
  language: string | null
  safety_issues: string[]
  safety_action: string
  groundedness_score: number
  hallucination_rate: number
  requires_teacher_review: boolean
  reviewed: boolean
  review_notes: string | null
  reviewed_at: string | null
  created_at: string | null
}

interface ReviewListResponse {
  traces: ReviewItem[]
  total: number
  limit: number
  offset: number
}

type FilterTab = 'pending' | 'resolved'

export default function AdminReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<FilterTab>('pending')

  const fetchItems = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data: ReviewListResponse = await fetchWithAuth(
        `/api/admin/review?status=${filter}&limit=50`
      )
      setItems(data.traces)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load review items')
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  const handleResolve = async (traceId: string, notes: string) => {
    try {
      await fetchWithAuth(`/api/admin/review/${traceId}`, {
        method: 'PATCH',
        body: JSON.stringify({ action: 'resolve', review_notes: notes }),
        headers: { 'Content-Type': 'application/json' },
      })
      fetchItems()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resolve item')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Review Queue</h1>
          <p className="text-sm text-gray-500 mt-1">
            Pipeline responses flagged by the Safety Node for teacher review
          </p>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setFilter('pending')}
          className={`px-4 py-2 text-sm rounded-lg ${
            filter === 'pending'
              ? 'bg-yellow-100 text-yellow-800 font-medium'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Pending ({filter === 'pending' ? total : '...'})
        </button>
        <button
          onClick={() => setFilter('resolved')}
          className={`px-4 py-2 text-sm rounded-lg ${
            filter === 'resolved'
              ? 'bg-green-100 text-green-800 font-medium'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Resolved
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      <ReviewQueue items={items} onResolve={handleResolve} loading={loading} />
    </div>
  )
}
```

- [ ] **Step 5: Verify dashboard builds**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -30
```
Expected: No type errors in new governance components (pre-existing errors may still appear)

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/app/admin/review/page.tsx dashboard/src/components/governance/
git commit -m "feat(governance): add review queue dashboard page"
```

---

### Task 3: Admin Nav Item

**Files:**
- Modify: `dashboard/src/app/admin/layout.tsx`

- [ ] **Step 1: Add nav item**

Add to the `NAV_ITEMS` array in `dashboard/src/app/admin/layout.tsx`:
```typescript
{ href: '/admin/review', label: 'Review Queue', icon: '🚩' },
```

Insert it after the existing Monitoring item (or at the end — order is by importance).

- [ ] **Step 2: Verify layout builds**

```bash
cd dashboard && npx tsc --noEmit 2>&1 | head -10
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/app/admin/layout.tsx
git commit -m "feat(governance): add Review Queue nav item to admin sidebar"
```

---

### Task 4: Final Verification

- [ ] **Step 1: Run backend tests**

```bash
.venv/bin/python -m pytest tests/test_admin_review.py tests/test_trace_repository.py tests/test_tracing_api.py -v --tb=short
```
Expected: All tests pass

- [ ] **Step 2: Lint check**

```bash
.venv/bin/ruff check src/api/admin.py
```
Expected: All checks passed

- [ ] **Step 3: Verify app imports**

```bash
.venv/bin/python -c "from src.main import app; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Final commit**

```bash
git add -A && git commit -m "chore: final verification for governance dashboard"
```
