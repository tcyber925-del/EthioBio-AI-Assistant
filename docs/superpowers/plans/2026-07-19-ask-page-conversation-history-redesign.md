# /ask Page Conversation History Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the /ask page from single-column layout to a split-panel layout with a persistent, searchable conversation history sidebar.

**Architecture:** Extract history data logic into a custom hook (`useConversationHistory`), build a `ConversationSidebar` component with date-grouped history items, refactor `page.tsx` to use a grid layout wrapped in `DashboardLayout`.

**Tech Stack:** Next.js 14 App Router, Tailwind CSS, Framer Motion, lucide-react, next-intl

---

### Task 1: `useConversationHistory` hook

**Files:**
- Create: `dashboard/src/hooks/useConversationHistory.ts`

Extract the history fetching, pairing, race-condition-guarding, and date-grouping logic from the current inline code into a reusable hook. The hook will be the single source of truth for all history state.

- [ ] **Step 1: Create the hook file**

```typescript
'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchWithTimeout } from '@/lib/fetch'
import { getToken, isAuthenticated } from '@/lib/auth'

export interface HistoryTurn {
  id: string
  session_id: string | null
  role: string
  content: string
  topic: string | null
  created_at: string
}

export interface QAPair {
  question: HistoryTurn
  answer: HistoryTurn | null
  id: string
}

export interface DateGroup {
  label: string
  items: QAPair[]
}

function getDateLabel(date: Date): string {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diffDays = Math.floor((today.getTime() - target.getTime()) / 86400000)

  if (diffDays === 0) return 'today'
  if (diffDays === 1) return 'yesterday'
  if (diffDays < 7) return 'this_week'
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function pairTurns(data: HistoryTurn[]): QAPair[] {
  const pairs: QAPair[] = []
  const sorted = [...data].reverse()
  for (let i = 0; i < sorted.length; i++) {
    if (sorted[i].role === 'user' && i + 1 < sorted.length && sorted[i + 1].role === 'assistant') {
      pairs.push({ question: sorted[i], answer: sorted[i + 1], id: sorted[i].id })
    }
  }
  return pairs
}

function groupByDate(pairs: QAPair[]): DateGroup[] {
  const map = new Map<string, QAPair[]>()
  for (const pair of pairs) {
    const label = getDateLabel(new Date(pair.question.created_at))
    if (!map.has(label)) map.set(label, [])
    map.get(label)!.push(pair)
  }
  const order = ['today', 'yesterday', 'this_week']
  const groups: DateGroup[] = []
  for (const key of order) {
    if (map.has(key)) groups.push({ label: key, items: map.get(key)! })
  }
  for (const [key, items] of map) {
    if (!order.includes(key)) groups.push({ label: key, items })
  }
  return groups
}

interface UseConversationHistoryReturn {
  history: QAPair[]
  dateGroups: DateGroup[]
  loading: boolean
  error: boolean
  fetchHistory: () => Promise<void>
}

export function useConversationHistory(limit = 50): UseConversationHistoryReturn {
  const [history, setHistory] = useState<QAPair[]>([])
  const [dateGroups, setDateGroups] = useState<DateGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const reqId = useRef(0)

  const fetchHistory = useCallback(async () => {
    if (!isAuthenticated()) return
    const id = ++reqId.current
    setLoading(true)
    setError(false)
    try {
      const token = getToken()
      const data: HistoryTurn[] = await fetchWithTimeout(`/api/v1/memory/conversations?limit=${limit}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (id !== reqId.current) return
      const pairs = pairTurns(data)
      if (id !== reqId.current) return
      setHistory(pairs)
      setDateGroups(groupByDate(pairs))
    } catch {
      if (id !== reqId.current) return
      setError(true)
    } finally {
      if (id === reqId.current) setLoading(false)
    }
  }, [limit])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  return { history, dateGroups, loading, error, fetchHistory }
}
```

- [ ] **Step 2: Verify the file parses**

Run: `npx tsc --noEmit dashboard/src/hooks/useConversationHistory.ts 2>&1 | head -20`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/hooks/useConversationHistory.ts
git commit -m "feat: add useConversationHistory hook with date grouping"
```

---

### Task 2: ConversationSidebar component

**Files:**
- Create: `dashboard/src/components/ConversationSidebar.tsx`

Build the sidebar panel that displays search input, date-grouped history items, and loading/empty/error states.

- [ ] **Step 1: Create the component file**

```tsx
'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Clock, Loader2, MessageSquare, Search, RefreshCw, AlertCircle } from 'lucide-react'
import type { DateGroup, QAPair } from '@/hooks/useConversationHistory'

interface ConversationSidebarProps {
  dateGroups: DateGroup[]
  loading: boolean
  error: boolean
  activeId: string | null
  onSelect: (pair: QAPair) => void
  onRefresh: () => void
}

export function ConversationSidebar({
  dateGroups,
  loading,
  error,
  activeId,
  onSelect,
  onRefresh,
}: ConversationSidebarProps) {
  const ta = useTranslations('ask')
  const [query, setQuery] = useState('')

  const filtered = query.trim()
    ? dateGroups.map(g => ({
        ...g,
        items: g.items.filter(i => i.question.content.toLowerCase().includes(query.toLowerCase())),
      })).filter(g => g.items.length > 0)
    : dateGroups

  return (
    <aside className="lg:col-span-1">
      <div className="rounded-[20px] border border-v2-border bg-v2-bg p-4 h-full flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <h3 className="verge-label text-v2-text-secondary">{ta('recent_questions')}</h3>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="text-v2-text-muted hover:text-v2-text-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="relative mb-3">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-v2-text-muted" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={ta('search_history')}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-v2-surface border border-v2-border rounded-lg text-v2-text-primary placeholder:text-v2-text-muted/50 focus:outline-none focus:ring-1 focus:ring-v2-accent"
          />
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 min-h-0 scrollbar-thin">
          {loading && (
            <div className="flex items-center gap-2 text-xs text-v2-text-muted py-4">
              <Loader2 className="w-3 h-3 animate-spin" />
              {ta('loading_history')}
            </div>
          )}

          {!loading && error && (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <p className="text-xs text-red-400">{ta('load_history_error')}</p>
              <button onClick={onRefresh} className="text-xs text-v2-accent hover:underline">
                {ta('retry')}
              </button>
            </div>
          )}

          {!loading && !error && filtered.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <MessageSquare className="w-5 h-5 text-v2-text-muted/40" />
              <p className="text-xs text-v2-text-muted">{query ? ta('no_search_results') : ta('no_history')}</p>
            </div>
          )}

          {!loading && !error && filtered.map(group => (
            <div key={group.label}>
              <h4 className="verge-label text-[10px] text-v2-text-muted mb-1.5 px-1">{ta(group.label)}</h4>
              <div className="space-y-1">
                {group.items.map(pair => (
                  <button
                    key={pair.id}
                    onClick={() => onSelect(pair)}
                    className={`w-full text-left p-2.5 rounded-xl border transition-colors ${
                      activeId === pair.id
                        ? 'border-v2-accent bg-v2-accent/5'
                        : 'border-transparent hover:border-v2-border hover:bg-v2-surface'
                    }`}
                  >
                    <p className="text-xs font-medium text-v2-text-primary line-clamp-1 leading-snug">
                      {pair.question.content}
                    </p>
                    {pair.answer && (
                      <p className="text-[11px] text-v2-text-muted mt-0.5 line-clamp-1 leading-snug">
                        {pair.answer.content}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/ConversationSidebar.tsx
git commit -m "feat: add ConversationSidebar component with search and date grouping"
```

---

### Task 3: Translation keys

**Files:**
- Modify: `dashboard/messages/en.json`
- Modify: `dashboard/messages/am.json`

Add the i18n keys used by the new components.

- [ ] **Step 1: Add English keys**

Add inside the `"ask"` object in `dashboard/messages/en.json`:

```json
    "search_history": "Search history",
    "no_history": "No questions yet",
    "no_search_results": "No matching questions",
    "today": "Today",
    "yesterday": "Yesterday",
    "this_week": "This Week",
    "retry": "Retry"
```

- [ ] **Step 2: Add Amharic keys**

Add inside the `"ask"` object in `dashboard/messages/am.json`:

```json
    "search_history": "ታሪክ ፈልግ",
    "no_history": "ገና ምንም ጥያቄዎች የሉም",
    "no_search_results": "ምንም የሚዛመዱ ጥያቄዎች የሉም",
    "today": "ዛሬ",
    "yesterday": "ትናንት",
    "this_week": "በዚህ ሳምንት",
    "retry": "ደግሞ ሞክር"
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/messages/en.json dashboard/messages/am.json
git commit -m "feat(i18n): add conversation history translation keys"
```

---

### Task 4: Refactor /ask page.tsx

**Files:**
- Modify: `dashboard/src/app/(dashboard)/ask/page.tsx`

Replace the entire page content with the new grid layout: wrap in `DashboardLayout`, split into `ChatArea` (2/3) and `ConversationSidebar` (1/3), wire state through the hook.

- [ ] **Step 1: Rewrite page.tsx**

```tsx
'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Send, MessageSquare, AlertTriangle, BookOpen, Loader2 } from 'lucide-react'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import ModelSelector from '@/components/ModelSelector'
import { DashboardLayout } from '@/components/dashboard-v2/DashboardLayout'
import { ConversationSidebar } from '@/components/ConversationSidebar'
import { useConversationHistory } from '@/hooks/useConversationHistory'
import { fetchWithTimeout } from '@/lib/fetch'
import { getUserId, isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

export default function AskPage() {
  const router = useRouter()
  const ta = useTranslations('ask')
  const tc = useTranslations('common')

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
  }, [router])

  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [sources, setSources] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [grade, setGrade] = useState(12)
  const [mode, setMode] = useState<'graph' | 'chat'>('graph')
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null)

  const {
    dateGroups,
    loading: loadingHistory,
    error: historyError,
    fetchHistory,
  } = useConversationHistory(50)

  const askQuestion = async () => {
    if (!question.trim()) return
    setLoading(true)
    setError(null)
    setAnswer(null)

    try {
      const endpoint = mode === 'graph' ? '/graph/chat' : '/chat'
      const body = mode === 'graph'
        ? { question: question.trim(), grade_level: grade, model: selectedModel }
        : { user_id: getUserId() || '00000000-0000-0000-0000-000000000001', question: question.trim(), grade_level: grade, use_rag: true, model: selectedModel }

      const data = await fetchWithTimeout(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }, 120000)

      setAnswer(data.answer || '')
      setSelectedModel(data.model_used || '')
      setConfidence(data.confidence || 0)
      setSources(data.sources || [])
      setActiveHistoryId(null)
      fetchHistory()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleHistorySelect = (pair: { question: { content: string }, answer: { content: string } | null, id: string }) => {
    setQuestion(pair.question.content)
    setAnswer(pair.answer?.content ?? null)
    setActiveHistoryId(pair.id)
    setSelectedModel('')
    setConfidence(0)
    setSources([])
  }

  const chatArea = (
    <div className="lg:col-span-2 space-y-5">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div />
        <div className="flex items-center gap-3">
          <ModelSelector value={selectedModel} onChange={setSelectedModel} />
          <select
            value={grade}
            onChange={e => setGrade(Number(e.target.value))}
            className="px-3 py-2 border border-v2-border rounded-lg text-sm bg-v2-bg text-v2-text-primary focus:outline-none focus:ring-1 focus:ring-v2-accent"
          >
            {[7, 8, 9, 10, 11, 12].map(g => (
              <option key={g} value={g}>{ta('grade_label')} {g}</option>
            ))}
          </select>
          <div className="flex border border-v2-border rounded-lg overflow-hidden">
            <button
              onClick={() => setMode('graph')}
              className={`px-3 py-2 text-xs font-medium transition-colors ${
                mode === 'graph' ? 'bg-v2-accent text-v2-inverted' : 'bg-v2-bg text-v2-text-muted hover:text-v2-text-primary'
              }`}
            >
              {ta('graph_mode')}
            </button>
            <button
              onClick={() => setMode('chat')}
              className={`px-3 py-2 text-xs font-medium transition-colors ${
                mode === 'chat' ? 'bg-v2-accent text-v2-inverted' : 'bg-v2-bg text-v2-text-muted hover:text-v2-text-primary'
              }`}
            >
              {ta('chat_mode')}
            </button>
          </div>
        </div>
      </div>

      {/* Input */}
      <div className="rounded-[20px] border border-v2-border bg-v2-bg p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && askQuestion()}
            placeholder={ta('example_placeholder')}
            className="flex-1 px-4 py-3 border border-v2-border rounded-lg text-sm bg-v2-surface text-v2-text-primary placeholder:text-v2-text-muted/50 focus:outline-none focus:ring-1 focus:ring-v2-accent"
          />
          <button
            onClick={askQuestion}
            disabled={loading || !question.trim()}
            className="px-6 py-3 bg-v2-accent text-v2-inverted rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-opacity"
          >
            {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> {ta('thinking')}...</> : <><Send className="w-4 h-4" /> {ta('ask_button')}</>}
          </button>
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="rounded-[20px] border border-v2-border bg-v2-bg p-8 text-center">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-v2-surface rounded w-3/4 mx-auto" />
            <div className="h-4 bg-v2-surface rounded w-1/2 mx-auto" />
            <div className="h-4 bg-v2-surface rounded w-2/3 mx-auto" />
          </div>
          <p className="text-sm text-v2-text-muted mt-4">{ta('calling_model', { model: selectedModel || 'model' })}</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-[20px] border border-red-500/20 bg-red-500/10 p-5 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium text-red-400">{tc('error')}</p>
            <p className="text-sm text-red-400/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Answer */}
      {answer && !loading && (
        <div className="rounded-[20px] border border-v2-border bg-v2-bg p-6">
          <div className="flex items-center gap-2 text-xs text-v2-text-muted mb-4 pb-3 border-b border-v2-border">
            <MessageSquare className="w-4 h-4" />
            <span className="font-mono">{selectedModel}</span>
            <span className="px-2 py-0.5 bg-v2-accent/10 text-v2-accent rounded-full text-xs">
              {Math.round(confidence * 100)}% {ta('confidence')}
            </span>
          </div>
          <MarkdownRenderer content={answer} />
          {sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-v2-border">
              <p className="text-xs text-v2-text-muted font-medium mb-2">{ta('sources')}</p>
              <div className="flex flex-wrap gap-2">
                {sources.map((s, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 bg-v2-accent/10 text-v2-accent rounded-full text-xs">
                    <BookOpen className="w-3 h-3" /> {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!answer && !loading && !error && (
        <div className="text-center py-16">
          <MessageSquare className="w-12 h-12 text-v2-text-muted/20 mx-auto mb-3" />
          <p className="text-v2-text-muted font-medium">{ta('no_questions')}</p>
          <p className="text-sm text-v2-text-muted/60 mt-1">{ta('no_questions_subtitle')}</p>
        </div>
      )}
    </div>
  )

  return (
    <DashboardLayout breadcrumbs={[{ label: ta('title') }]}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {chatArea}
        <ConversationSidebar
          dateGroups={dateGroups}
          loading={loadingHistory}
          error={historyError}
          activeId={activeHistoryId}
          onSelect={handleHistorySelect}
          onRefresh={fetchHistory}
        />
      </div>
    </DashboardLayout>
  )
}
```

- [ ] **Step 2: Verify the page renders**

Run: `npx tsc --noEmit dashboard/src/app/\(dashboard\)/ask/page.tsx 2>&1 | head -30`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/app/\(dashboard\)/ask/page.tsx
git commit -m "feat: refactor /ask page to split-panel layout with ConversationSidebar"
```

---

### Task 5: Lint + typecheck

- [ ] **Step 1: Run lint**

Run: `ruff check src/ && npx next lint` from the dashboard directory.
Expected: all checks pass.

- [ ] **Step 2: Push and create PR**

```bash
git push -u origin clean/fix-student-lesson-data
gh pr create --title "feat: redesign /ask page with persistent conversation history sidebar" --body "Redesigns the /ask Q&A page with a split-panel layout: chat area (2/3) on the left and persistent ConversationSidebar (1/3) on the right. The sidebar shows date-grouped history with search, loading/empty/error states, and click-to-restore. Extracts history data logic into useConversationHistory hook. Adds i18n keys for English and Amharic."
```
