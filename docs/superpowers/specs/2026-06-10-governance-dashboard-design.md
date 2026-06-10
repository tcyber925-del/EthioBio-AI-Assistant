# Governance Dashboard — Design Spec

**Date:** 2026-06-10
**Status:** Draft
**PRD:** PRD-009 — Agentic RAG Governance, Evaluation, and Observability (sub-project 4)

## Overview

Admin dashboard for reviewing pipeline responses flagged by the Safety Node. Teachers can view flagged content, add review notes, and mark items as resolved.

**Scope:** Flagged pipeline responses only (not content moderation for lessons/quizzes). View + add notes + resolve workflow. Lives as an admin sub-page at `/admin/review`.

## Architecture

```
PipelineMonitor → TraceRepository → agent_traces (PostgreSQL)
                                          │
                                    GET /admin/review (list flagged)
                                          │
                                    PATCH /admin/review/{id} (resolve)
                                          │
                                    Next.js /admin/review (dashboard UI)
```

- Flagged items are pipeline traces where `event_metadata` contains `requires_teacher_review: true`
- Review actions are stored in the trace's `event_metadata` JSONB (no new DB model)
- Dashboard is an admin sub-page with existing auth checks

## Backend API

### `GET /admin/review`

List traces requiring teacher review. Added to existing `src/api/admin.py` router.

Query params:
- `status` — `"pending"` (default) or `"resolved"`
- `limit` — default 50, max 200
- `offset` — default 0

Response:
```json
{
  "traces": [
    {
      "trace_id": "...",
      "user_message": "What is...",
      "response": "...",
      "intent": "tutor",
      "grade_level": 8,
      "language": "en",
      "safety_issues": ["profanity", "misinformation"],
      "groundedness_score": 0.3,
      "hallucination_rate": 0.15,
      "safety_action": "revise",
      "requires_teacher_review": true,
      "reviewed": false,
      "review_notes": null,
      "reviewed_at": null,
      "created_at": "2026-06-10T12:00:00Z"
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

### `PATCH /admin/review/{trace_id}`

Mark a trace as reviewed.

Request:
```json
{
  "action": "resolve",
  "review_notes": "Student asked about... Response was appropriate but... Reviewed and approved."
}
```

Response:
```json
{
  "trace_id": "trace_abc123",
  "status": "resolved",
  "reviewed_at": "2026-06-10T12:30:00Z"
}
```

The handler:
1. Queries `agent_traces` by trace_id
2. Updates `event_metadata` with `reviewed: true`, `reviewed_at`, `reviewed_by` (from auth), `review_notes`
3. Commits and returns updated status

Errors:
- 404 if trace_id not found
- 400 if trace doesn't require review
- 500 for unexpected errors

## Data Model

No new models. Review state stored in `agent_traces.event_metadata` JSONB:

```json
{
  "requires_teacher_review": true,
  "safety_issues": ["...", "..."],
  "safety_action": "revise",
  "reviewed": true,
  "reviewed_at": "2026-06-10T12:30:00Z",
  "reviewed_by": "teacher-uuid",
  "review_notes": "Reviewed and approved."
}
```

## Frontend

### Page: `/admin/review`

Next.js client component (like existing admin pages). Two views:

1. **List View** — table showing flagged traces:
   - Timestamp (relative: "2 hours ago")
   - User message (truncated to 100 chars)
   - Intent badge (tutor/quiz/lesson)
   - Safety issues (comma-separated tags)
   - Status badge (pending = yellow, resolved = green)
   - Action button (Review / Reviewed)

2. **Detail Panel** — expandable row showing:
   - Full user message and response
   - Safety issues list
   - Groundedness / hallucination scores
   - Ungrounded claims (if any)
   - Review notes textarea + action buttons (Resolve / Dismiss)

### Auth

Leverages existing admin auth — only users with `admin` role can access. The existing `admin/layout.tsx` checks for 403 on mount.

### Nav Item

Add "Review Queue" to the admin sidebar in `admin/layout.tsx`:
```typescript
{ href: '/admin/review', label: 'Review Queue', icon: '🚩' }
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| ReviewQueue | `components/governance/ReviewQueue.tsx` | List table with filters |
| ReviewDetail | `components/governance/ReviewDetail.tsx` | Expandable detail + action |
| ReviewNotesModal | `components/governance/ReviewNotesModal.tsx` | Resolve confirmation with notes |

## File Map

| Action | Path |
|--------|------|
| Modify | `src/api/admin.py` (add review endpoints + schemas) |
| Create | `dashboard/src/app/admin/review/page.tsx` |
| Create | `dashboard/src/components/governance/ReviewQueue.tsx` |
| Create | `dashboard/src/components/governance/ReviewDetail.tsx` |
| Create | `dashboard/src/components/governance/ReviewNotesModal.tsx` |
| Modify | `dashboard/src/app/admin/layout.tsx` (add nav item) |
| Create | `tests/test_admin_review.py` |

## Test Plan

- **Backend unit:** `GET /admin/review` returns correct items with pagination
- **Backend unit:** `PATCH /admin/review/{id}` updates metadata correctly
- **Backend unit:** 404 for missing trace, 400 for not-flagged trace
- **Backend unit:** Auth enforcement via `require_admin`
