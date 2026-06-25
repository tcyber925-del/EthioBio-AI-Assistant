# Agent Orchestrator Dashboard Design

**Date:** 2026-06-24
**Status:** Approved
**PRD:** PRD-010 — Educational Multi-Agent Intelligence System (EMAIS)

## Scope

Admin-only dashboard at `/admin/agents` displaying the 8 registered agents, allowing ad-hoc task execution, and showing reflection history. MVP covers: registry view, execution panel, reflection log.

## Backend Changes

### Reflection Persistence (`src/core/agent_orchestrator/orchestrator.py`)

- Add `_reflections: list[AgentReflection]` to `AgentOrchestrator.__init__()`
- `_record_reflection()` appends to this list (was structlog-only)
- Add `get_reflections(limit: int = 20) -> list[AgentReflection]` returning most recent N

No DB needed for MVP — in-memory only. Survives within process lifetime.

### New API Endpoint (`src/api/agent_orchestrator.py`)

```
GET /agents/reflections?limit=20
Response: [{agent, task, verdict, confidence, duration_ms, error, timestamp}]
```

No changes to `GET /agents`, `GET /agents/capabilities`, `POST /agents/execute` — all work as-is.

## Frontend Changes

### Page: `/admin/agents` → `dashboard/src/app/admin/agents/page.tsx`

Standard admin page pattern (`'use client'`, `fetchWithAuth`, loading/error/data states, `export const dynamic = 'force-dynamic'`).

### Three-Section Layout

| Section | Component | API | Position |
|---------|-----------|-----|----------|
| Agent Registry Grid | `AgentCard` (4-col grid) | `GET /agents` | Top |
| Task Execution Panel | `ExecutionPanel` | `POST /agents/execute` | Middle |
| Reflection History | `ReflectionTable` | `GET /agents/reflections?limit=20` | Bottom |

After execution, auto-refresh reflection table.

### New Components

All in `dashboard/src/components/agents/`:

1. **AgentCard.tsx** — Shows name, description, capability badges, status badge, version. Card variant maps to status (idle=default, busy=accent, error=elevated with red border).

2. **ExecutionPanel.tsx** — Agent dropdown, task textarea, Execute button with loading spinner. Result area below showing confidence gauge bar, duration, verdict badge, and result text or error.

3. **ReflectionTable.tsx** — Table with columns: Agent, Task (truncated), Verdict badge (pass=green, fail=red, inconclusive=yellow), Confidence bar, Duration, Time ago, Error. Refresh button in header.

### Admin Nav

Add to `NAV_ITEMS` in `dashboard/src/app/admin/layout.tsx`:
```
{ label: "Agents", href: "/admin/agents", icon: Cpu }
```

### API Proxy

Add to `dashboard/next.config.js` `rewrites` array:
```
{ source: '/agents/:path*', destination: `${api}/agents/:path*` }
```

## Data Types

```typescript
interface AgentInfo {
  name: string;
  description: string;
  capabilities: string[];
  status: "idle" | "busy" | "error";
  version: string;
}

interface ExecutionResult {
  task_id: string;
  agent: string;
  result: string;
  confidence: number;
  duration_ms: number;
  error: string | null;
}

interface AgentReflection {
  agent: string;
  task: string;
  verdict: "pass" | "fail" | "inconclusive";
  confidence: number;
  duration_ms: number;
  error: string | null;
  timestamp: string;
}
```

## States

- **Loading:** CardSkeleton grid for agents (4 skeleton cards), skeleton for execution panel, TableSkeleton(5) for reflections
- **Error:** AlertTriangle icon with error message and "Retry" button for each section independently
- **Empty agents:** "No agents registered. Check that the orchestrator is running." — full-page centered message
- **Empty reflections:** "No executions yet. Run a task above to see results here."
- **Execution error:** Red result box with error text and "Try again" option

## Files Changed / Created

| File | Action |
|------|--------|
| `src/core/agent_orchestrator/orchestrator.py` | Modify — add `_reflections` list + `get_reflections()` |
| `src/api/agent_orchestrator.py` | Modify — add `GET /agents/reflections` endpoint |
| `dashboard/next.config.js` | Modify — add `/agents/:path*` proxy |
| `dashboard/src/app/admin/layout.tsx` | Modify — add "Agents" nav item |
| `dashboard/src/app/admin/agents/page.tsx` | Create — main page |
| `dashboard/src/components/agents/AgentCard.tsx` | Create |
| `dashboard/src/components/agents/ExecutionPanel.tsx` | Create |
| `dashboard/src/components/agents/ReflectionTable.tsx` | Create |
