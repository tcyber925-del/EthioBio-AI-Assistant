# Agent Orchestrator Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an admin dashboard page at `/admin/agents` showing registered agents, task execution, and reflection history.

**Architecture:** Backend — singleton `AgentOrchestrator` with in-memory reflection list + new `GET /agents/reflections` endpoint. Frontend — single admin page with three sections (agent grid, execution panel, reflection table) following existing admin patterns.

**Tech Stack:** FastAPI (backend), Next.js 14 App Router (frontend), Tailwind CSS, lucide-react icons

---
### Task 1: Singleton Orchestrator + Reflection Storage

**Files:**
- Modify: `src/core/agent_orchestrator/orchestrator.py:21-24,180-189`
- Test: Self-review (no new tests for in-memory storage)

**Problem:** `_get_orchestrator()` in the API module creates a new orchestrator on every request, so in-memory reflections vanish immediately. Need a module-level singleton.

- [ ] **Step 1: Add singleton cache to orchestrator.py**

Add at module level, after `logger = structlog.get_logger()`:

```python
_orchestrator_cache: dict[str, AgentOrchestrator] = {}
```

- [ ] **Step 2: Add `_reflections` list + `get_reflections()` to `AgentOrchestrator`**

Replace `self._messages: list[AgentMessage] = []` with:
```python
self._reflections: list[AgentReflection] = []
```

Replace the empty `_record_reflection(self, reflection)` with:
```python
def _record_reflection(self, reflection: AgentReflection) -> None:
    self._reflections.append(reflection)
    logger.info(
        "agent_reflection",
        agent=reflection.agent_name,
        verdict=reflection.verdict.value,
        duration_ms=reflection.duration_ms,
    )
```

Replace `get_reflections(self, agent_name=None)` with:
```python
def get_reflections(self, limit: int = 20) -> list[AgentReflection]:
    sorted_refs = sorted(self._reflections, key=lambda r: r.created_at, reverse=True)
    return sorted_refs[:limit]
```

- [ ] **Step 3: Verify no regression**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant && python -c "from src.core.agent_orchestrator import AgentOrchestrator, AgentRegistry; o = AgentOrchestrator(AgentRegistry()); print(o.get_reflections())"`
Expected: `[]`

- [ ] **Step 4: Commit**

```bash
git add src/core/agent_orchestrator/orchestrator.py
git commit -m "feat(agents): add in-memory reflection storage to orchestrator"
```

---
### Task 2: Singleton Builder + Reflections API Endpoint

**Files:**
- Modify: `src/api/agent_orchestrator.py:44-47,89`
- Test: `tests/test_agent_orchestrator_api.py` (new)

- [ ] **Step 1: Add singleton caching to `_get_orchestrator()`**

Replace the function:
```python
from src.core.agent_orchestrator import AgentOrchestrator, build_orchestrator
from src.llm.router import ModelRouter
from src.retrieval.adapter import VectorStoreAdapter

_orchestrator_instance: AgentOrchestrator | None = None

def _get_orchestrator() -> AgentOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        router_llm = ModelRouter()
        adapter = VectorStoreAdapter()
        _orchestrator_instance = build_orchestrator(router_llm, adapter)
    return _orchestrator_instance
```

- [ ] **Step 2: Add `GET /agents/reflections` endpoint**

Add new schema before `_get_orchestrator`:

```python
from datetime import datetime

class ReflectionInfo(SchemaModel):
    agent: str
    task: str
    verdict: str
    confidence: float
    duration_ms: int
    error: str | None = None
    timestamp: datetime | None = None
```

Add new endpoint after `list_capabilities`:

```python
@router.get("/reflections", response_model=list[ReflectionInfo])
async def list_reflections(limit: int = 20):
    orchestrator = _get_orchestrator()
    return [
        ReflectionInfo(
            agent=r.agent_name,
            task=r.objective,
            verdict=r.verdict.value,
            confidence=r.confidence,
            duration_ms=r.duration_ms,
            error=r.error,
            timestamp=r.created_at,
        )
        for r in orchestrator.get_reflections(limit)
    ]
```

- [ ] **Step 3: Write a test for the new endpoint**

Create `tests/test_agent_orchestrator_api.py`:

```python
"""Tests for the agent orchestrator API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.anyio
async def test_list_agents_endpoint(client):
    async with client as ac:
        resp = await ac.get("/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_list_reflections_empty(client):
    async with client as ac:
        resp = await ac.get("/agents/reflections?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_list_capabilities(client):
    async with client as ac:
        resp = await ac.get("/agents/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_execute_endpoint_missing_agent(client):
    async with client as ac:
        resp = await ac.post("/agents/execute", json={
            "task": "test task",
            "preferred_agent": "nonexistent_agent",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
```

- [ ] **Step 4: Run tests**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant && .venv/bin/pytest tests/test_agent_orchestrator_api.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/api/agent_orchestrator.py tests/test_agent_orchestrator_api.py
git commit -m "feat(agents): add GET /agents/reflections endpoint with singleton orchestrator"
```

---
### Task 3: Add /agents/ Proxy Rewrite

**Files:**
- Modify: `dashboard/next.config.js:14`

- [ ] **Step 1: Add agents rewrite**

Add after the `/diagram/:path*` line:
```javascript
      { source: '/agents/:path*', destination: `${api}/agents/:path*` },
```

- [ ] **Step 2: Verify syntax**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant/dashboard && node -e "require('./next.config.js')"`
Expected: no output (no error)

- [ ] **Step 3: Commit**

```bash
git add dashboard/next.config.js
git commit -m "feat(agents): add /agents/:path* proxy to next.config.js"
```

---
### Task 4: Add "Agents" to Admin Nav

**Files:**
- Modify: `dashboard/src/app/admin/layout.tsx:15`

- [ ] **Step 1: Add Agents nav item**

Add after `{ href: '/admin/monitoring', label: 'Monitoring', icon: '📡' },`:
```javascript
  { href: '/admin/agents', label: 'Agents', icon: '🤖' },
```

- [ ] **Step 2: Verify no TypeScript errors**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant/dashboard && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: no errors (any existing pre-existing errors are fine)

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/app/admin/layout.tsx
git commit -m "feat(agents): add Agents nav item to admin sidebar"
```

---
### Task 5: Create AgentCard Component

**Files:**
- Create: `dashboard/src/components/agents/AgentCard.tsx`
- Test: Visual inspection

- [ ] **Step 1: Create AgentCard component**

```tsx
'use client'

import Badge from '@/components/ui/Badge'
import Card from '@/components/ui/Card'

export interface AgentInfo {
  name: string
  description: string
  capabilities: string[]
  status: 'idle' | 'busy' | 'error'
  version: string
}

interface AgentCardProps {
  agent: AgentInfo
}

const statusBadge: Record<string, { variant: 'green' | 'yellow' | 'red'; label: string }> = {
  idle: { variant: 'green', label: 'Idle' },
  busy: { variant: 'yellow', label: 'Busy' },
  error: { variant: 'red', label: 'Error' },
}

const capabilityColors: Record<string, 'blue' | 'purple' | 'orange' | 'green' | 'red' | 'muted'> = {
const capabilityColors: Record<string, 'blue' | 'purple' | 'orange' | 'green' | 'muted'> = {
  tutoring: 'blue',
  quiz_generation: 'purple',
  assessment_creation: 'purple',
  lesson_planning: 'orange',
  diagnostic_assessment: 'blue',
  translation: 'green',
  safety_review: 'red',
  diagram_generation: 'purple',
  student_progress: 'blue',
}

export default function AgentCard({ agent }: AgentCardProps) {
  const s = statusBadge[agent.status] || statusBadge.idle

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-subhead font-semibold text-foreground">{agent.name}</h3>
          <p className="text-small text-foreground-muted mt-0.5">{agent.description}</p>
        </div>
        <Badge variant={s.variant}>{s.label}</Badge>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {agent.capabilities.map(cap => (
          <Badge key={cap} variant={capabilityColors[cap] || 'muted'}>
            {cap.replace(/_/g, ' ')}
          </Badge>
        ))}
      </div>
      <div className="text-xs text-foreground-muted">v{agent.version}</div>
    </Card>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant/dashboard && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: no errors for this file

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/agents/AgentCard.tsx
git commit -m "feat(agents): add AgentCard component"
```

---
### Task 6: Create ExecutionPanel Component

**Files:**
- Create: `dashboard/src/components/agents/ExecutionPanel.tsx`

- [ ] **Step 1: Create ExecutionPanel component**

```tsx
'use client'

import { useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import type { AgentInfo } from './AgentCard'

interface ExecutionResult {
  task_id: string
  agent: string
  result: string | Record<string, unknown>
  confidence: number
  duration_ms: number
  error: string | null
}

interface ExecutionPanelProps {
  agents: AgentInfo[]
  onExecute: () => void
}

export default function ExecutionPanel({ agents, onExecute }: ExecutionPanelProps) {
  const [selectedAgent, setSelectedAgent] = useState('')
  const [task, setTask] = useState('')
  const [result, setResult] = useState<ExecutionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleExecute = async () => {
    if (!selectedAgent || !task.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await fetchWithAuth('/agents/execute', {
        method: 'POST',
        body: JSON.stringify({ task: task.trim(), preferred_agent: selectedAgent }),
        headers: { 'Content-Type': 'application/json' },
      })
      setResult(data as ExecutionResult)
      onExecute()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="mt-6">
      <h2 className="text-heading text-foreground mb-4">Execute Task</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-small text-foreground-muted mb-1">Agent</label>
          <select
            value={selectedAgent}
            onChange={e => setSelectedAgent(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground text-body focus:outline-none focus:border-primary"
          >
            <option value="">Select an agent...</option>
            {agents.map(a => (
              <option key={a.name} value={a.name}>{a.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-small text-foreground-muted mb-1">Task</label>
          <textarea
            value={task}
            onChange={e => setTask(e.target.value)}
            rows={3}
            placeholder="Describe the task for the agent..."
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground text-body focus:outline-none focus:border-primary resize-none"
          />
        </div>
        <Button
          variant="primary"
          onClick={handleExecute}
          loading={loading}
          disabled={!selectedAgent || !task.trim() || loading}
        >
          {loading ? 'Executing...' : 'Execute'}
        </Button>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-body">
            {error}
          </div>
        )}

        {result && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={result.error ? 'red' : 'green'}>
                {result.error ? 'Failed' : 'Success'}
              </Badge>
              <span className="text-small text-foreground-muted">
                {result.duration_ms}ms
              </span>
              {result.confidence > 0 && (
                <div className="flex items-center gap-1 ml-auto">
                  <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${Math.round(result.confidence * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-foreground-muted">
                    {Math.round(result.confidence * 100)}%
                  </span>
                </div>
              )}
            </div>
            <pre className="text-small text-foreground whitespace-pre-wrap font-mono bg-background rounded p-2 max-h-48 overflow-y-auto">
              {typeof result.result === 'string'
                ? result.result
                : JSON.stringify(result.result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </Card>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant/dashboard && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: no errors for this file

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/agents/ExecutionPanel.tsx
git commit -m "feat(agents): add ExecutionPanel component"
```

---
### Task 7: Create ReflectionTable Component

**Files:**
- Create: `dashboard/src/components/agents/ReflectionTable.tsx`

- [ ] **Step 1: Create ReflectionTable component**

```tsx
'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { TableSkeleton } from '@/components/Skeleton'

export interface ReflectionInfo {
  agent: string
  task: string
  verdict: string
  confidence: number
  duration_ms: number
  error: string | null
  timestamp: string | null
}

function timeAgo(ts: string | null): string {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const verdictBadge: Record<string, 'green' | 'red' | 'yellow'> = {
  success: 'green',
  failure: 'red',
  partial: 'yellow',
}

export default function ReflectionTable({ refreshKey }: { refreshKey: number }) {
  const [reflections, setReflections] = useState<ReflectionInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchReflections = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithAuth('/agents/reflections?limit=20')
      setReflections(data as ReflectionInfo[])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchReflections() }, [refreshKey])

  if (loading) return <TableSkeleton rows={5} />
  if (error) return (
    <div className="flex items-center gap-2 text-red-400 text-body">
      <span>Failed to load reflections</span>
      <Button variant="ghost" onClick={fetchReflections}>Retry</Button>
    </div>
  )

  return (
    <Card className="mt-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-heading text-foreground">Recent Executions</h2>
        <Button variant="ghost" onClick={fetchReflections}>Refresh</Button>
      </div>
      {reflections.length === 0 ? (
        <p className="text-body text-foreground-muted text-center py-8">
          No executions yet. Run a task above to see results here.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-body">
            <thead>
              <tr className="border-b border-border text-small text-foreground-muted">
                <th className="text-left py-2 pr-4">Agent</th>
                <th className="text-left py-2 pr-4">Task</th>
                <th className="text-left py-2 pr-4">Verdict</th>
                <th className="text-right py-2 pr-4">Confidence</th>
                <th className="text-right py-2 pr-4">Duration</th>
                <th className="text-right py-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {reflections.map((r, i) => (
                <tr key={i} className="border-b border-border/50 text-foreground">
                  <td className="py-2 pr-4 font-medium">{r.agent}</td>
                  <td className="py-2 pr-4 max-w-xs truncate text-foreground-muted" title={r.task}>
                    {r.task}
                  </td>
                  <td className="py-2 pr-4">
                    <Badge variant={verdictBadge[r.verdict] || 'yellow'}>{r.verdict}</Badge>
                  </td>
                  <td className="py-2 pr-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <div className="w-12 h-1.5 bg-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${Math.round(r.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs">{Math.round(r.confidence * 100)}%</span>
                    </div>
                  </td>
                  <td className="py-2 pr-4 text-right text-foreground-muted">{r.duration_ms}ms</td>
                  <td className="py-2 text-right text-foreground-muted text-small">{timeAgo(r.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant/dashboard && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: no errors for this file

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components/agents/ReflectionTable.tsx
git commit -m "feat(agents): add ReflectionTable component"
```

---
### Task 8: Create /admin/agents Page

**Files:**
- Create: `dashboard/src/app/admin/agents/page.tsx`

- [ ] **Step 1: Create the page**

```tsx
'use client'

import { useEffect, useState, useCallback } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import PageHeader from '@/components/ui/PageHeader'
import { CardSkeleton } from '@/components/Skeleton'
import { Cpu, AlertTriangle, RefreshCw } from 'lucide-react'
import AgentCard from '@/components/agents/AgentCard'
import type { AgentInfo } from '@/components/agents/AgentCard'
import ExecutionPanel from '@/components/agents/ExecutionPanel'
import ReflectionTable from '@/components/agents/ReflectionTable'

export const dynamic = 'force-dynamic'

export default function AdminAgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const fetchAgents = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithAuth('/agents')
      setAgents(data as AgentInfo[])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAgents() }, [fetchAgents])

  const handleExecute = () => {
    setRefreshKey(k => k + 1)
  }

  if (error && agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <AlertTriangle className="w-12 h-12 text-red-400" />
        <p className="text-body text-red-400">{error}</p>
        <button
          onClick={fetchAgents}
          className="flex items-center gap-2 text-primary hover:underline text-subhead"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        icon={<Cpu className="w-6 h-6" />}
        title="Agent Orchestrator"
        description="Registered agents, task execution, and execution history"
      />

      {/* Section 1: Agent Registry Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 mt-6">
          <Cpu className="w-10 h-10 text-foreground-muted" />
          <p className="text-body text-foreground-muted">
            No agents registered. Check that the orchestrator is running.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {agents.map(agent => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      )}

      {/* Section 2: Task Execution */}
      <ExecutionPanel agents={agents} onExecute={handleExecute} />

      {/* Section 3: Reflection History */}
      <ReflectionTable refreshKey={refreshKey} />
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant/dashboard && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: no new errors

- [ ] **Step 3: Verify end-to-end (manual)**

1. Start the API: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant && python -m src.main`
2. In another terminal, test: `curl http://localhost:8000/agents | python -m json.tool`
   Expected: list of 8 agents
3. Test reflections: `curl http://localhost:8000/agents/reflections?limit=5`
   Expected: `[]`
4. Test execute: `curl -X POST http://localhost:8000/agents/execute -H "Content-Type: application/json" -d '{"task":"explain mitosis","preferred_agent":"tutor_agent"}' | python -m json.tool`
   Expected: result or error (agent may need Ollama, but endpoint returns something)

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/app/admin/agents/page.tsx
git commit -m "feat(agents): add /admin/agents dashboard page"
```

---
### Task 9: Lint + Typecheck + Test

**Files:** All

- [ ] **Step 1: Ruff check backend**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant && .venv/bin/ruff check src/core/agent_orchestrator/orchestrator.py src/api/agent_orchestrator.py`
Expected: no errors

- [ ] **Step 2: Mypy check backend**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant && .venv/bin/mypy src/core/agent_orchestrator/orchestrator.py src/api/agent_orchestrator.py`
Expected: no errors

- [ ] **Step 3: TypeScript check frontend**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant/dashboard && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: no new errors (pre-existing errors in other files are acceptable)

- [ ] **Step 4: Run backend tests**

Run: `cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio AI Assistant && .venv/bin/pytest tests/test_agent_orchestrator_api.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "chore: lint and typecheck agent orchestrator dashboard"
```
