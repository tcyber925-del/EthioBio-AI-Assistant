# /ask Page — Conversation History Redesign

**Date:** 2026-07-19
**Status:** Draft

## Problem

The `/ask` page renders Q&A in a single-column layout with a collapsible history list at the bottom. Users cannot browse, search, or easily navigate past conversations. The history feature exists but is visually buried.

## Goals

1. Make recent Q&A history persistently visible and browsable
2. Support search/filter within history
3. Group conversations by date for easier navigation
4. Follow existing DashboardV2 design patterns (grid split, ContextHeader, verge-label typography)
5. Require zero backend changes — the existing `GET /api/v1/memory/conversations` endpoint already returns all needed data

## Non-Goals

- Message editing/deletion (no backend support)
- Real-time updates / WebSocket (polling adds complexity without clear benefit)
- Chat-bubble messaging UI (Q&A pairs are the pattern, not a threaded chat)
- Separate `/history` route (keeping everything on `/ask` is simpler)

## Design

### Layout

The page wraps in `DashboardLayout` to get a `ContextHeader` breadcrumb ("Ask Q&A") and an animated main area. Inside the main area, a two-column grid:

```
┌──────────────────────────────────────────────────────────┐
│  ContextHeader  Ask Q&A                                  │
├────────────────────────────────┬─────────────────────────┤
│  ChatArea (lg:col-span-2)      │  ConversationSidebar     │
│                                │                         │
│  [controls: model, grade,      │  🔍 Search history...    │
│   mode toggle]                 │                         │
│                                │  📅 Today               │
│  ┌─input────────────────────┐  │  ├ What is DNA rep...   │
│  │ [Ask a question...] [Ask]│  │  ├ Explain mitosis      │
│  └──────────────────────────┘  │  ├ Protein synthesis    │
│                                │                         │
│  ┌─answer──────────────────┐  │  📅 Yesterday            │
│  │  (MarkdownRenderer)      │  │  ├ Cell structure       │
│  │                          │  │  ├ Evolution theory     │
│  │  Sources: [...]          │  │                         │
│  └──────────────────────────┘  │                         │
│                                │                         │
│  (empty/loading/error states)  │  (loading/empty/        │
│                                │   error states)         │
└────────────────────────────────┴─────────────────────────┘
```

### Component Tree

```
AskPage
├── DashboardLayout (breadcrumbs, animated main)
│   └── <main> (grid grid-cols-1 lg:grid-cols-3 gap-6)
│       ├── ChatArea (lg:col-span-2)
│       │   ├── ControlBar
│       │   │   ├── ModelSelector
│       │   │   ├── GradeSelect
│       │   │   └── ModeToggle (graph/chat)
│       │   ├── QuestionInput
│       │   ├── AnswerDisplay
│       │   │   ├── LoadingSkeleton
│       │   │   ├── ErrorBanner
│       │   │   ├── AnswerContent (MarkdownRenderer)
│       │   │   └── SourcesList
│       │   └── EmptyState
│       └── ConversationSidebar
│           ├── SearchInput
│           ├── LoadingState
│           ├── EmptyState
│           ├── ErrorState
│           └── DateGroup[]
│               └── HistoryItem[]
│                   ├── Question preview (truncated)
│                   ├── Answer preview (truncated, 1 line)
│                   ├── Timestamp (verge-label)
│                   └── Active indicator (highlight when selected)
```

### State Management

All local `useState` in `AskPage`:

| State | Type | Purpose |
|-------|------|---------|
| `question` | string | Current input value |
| `answer` | string \| null | Current answer |
| `history` | QAPair[] | Paired Q&A turns |
| `searchQuery` | string | History filter text |
| `activeHistoryId` | string \| null | Currently selected history item |
| `loading` | boolean | Question submission in flight |
| `loadingHistory` | boolean | History fetch in flight |
| `historyError` | boolean | History fetch failed |
| `sidebarOpen` | boolean | Mobile sidebar toggle (default open on desktop) |

### Data Flow

1. **On mount**: `GET /api/v1/memory/conversations?limit=50` → group by date → render `ConversationSidebar`
2. **After asking question**: On success, re-fetch history (same endpoint) to include the new turn
3. **Click history item**: Set `question` + `answer` + `activeHistoryId` → user can review and optionally edit question + re-ask. Note: metadata (sources, confidence, model) is not stored per-history-item — these are cleared on click since the displayed metadata belongs to the *current* answer, not the history item.
4. **Search**: Client-side filter on `question.content` (no debounce needed for 50 items)
5. **No polling/SSE**: Refresh only on new question or manual refresh button

**`useConversationHistory` hook interface:**
```typescript
function useConversationHistory(): {
  history: QAPair[]
  loadingHistory: boolean
  historyError: boolean
  fetchHistory: () => Promise<void>
}
```
The hook calls `GET /api/v1/memory/conversations?limit=50`, pairs the flat turns into QAPairs via the pairing logic below, groups them by date, and returns the structured result.

### History Pairing Logic

The raw `ConversationTurn` records come as flat, chronological items. Pair them:

1. Sort ascending by `created_at`
2. Iterate: for each `role === 'user'` record at index `i`, pair with `role === 'assistant'` at `i + 1` (if it exists)
3. If an odd record has no partner, skip it (orphan)

### Date Grouping

Group paired items into date buckets:
- "Today" (same calendar day)
- "Yesterday"
- "This Week" (within 7 days, not today/yesterday)
- Date string (e.g., "Jul 15") for older items

### Mobile Behavior

Below `lg` breakpoint, the grid collapses to single column. The `ConversationSidebar` becomes a toggleable overlay or slides in below the chat area, controlled by `sidebarOpen` state and a hamburger/back button.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| History fetch fails | `historyError = true`, sidebar shows inline error + retry button |
| Question submit fails | Existing error banner shown in ChatArea |
| Empty history (new user) | Sidebar shows "No questions yet" empty state |
| API returns 401 | Redirect to `/login` (existing auth check) |

## File Changes

| File | Change |
|------|--------|
| `dashboard/src/app/(dashboard)/ask/page.tsx` | Refactor to grid layout, add `DashboardLayout` wrapper, wire sidebar state |
| `dashboard/src/components/ConversationSidebar.tsx` | **New** — history list with search, date groups |
| `dashboard/src/components/HistoryItem.tsx` | **New** — single history row (or inline in Sidebar) |
| `dashboard/src/hooks/useConversationHistory.ts` | **New** — fetch + pair + group logic |
| `dashboard/messages/en.json` | Add `search_history`, `no_history`, `today`, `yesterday` keys |
| `dashboard/messages/am.json` | Same keys in Amharic |

No backend changes needed.

## Backward Compatibility

Existing `/ask` URL and behavior preserved. The page still works with collapsed sidebar (mobile). Old `history` query params or deep links unaffected since there are none.
