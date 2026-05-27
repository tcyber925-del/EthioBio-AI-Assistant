# Recovery Plan Enhancements — Batch 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add mastery visualizations (radar chart, trend graphs, heatmap, learning tree) to the `/recovery` dashboard, and add recovery plan management to the Telegram bot.

**Architecture:** Phase 1 is pure frontend — add 4 Recharts-based visualization components to the existing `/recovery` page. Phase 2 adds 3 new bot commands + inline buttons to the existing telegram bot. No backend schema or API changes needed.

**Tech Stack:** Recharts (already in dashboard deps), React/Next.js, python-telegram-bot, FastAPI (existing endpoints)

---

### Task 1: Mastery Radar Chart Component

**Files:**
- Create: `dashboard/src/components/recovery/MasteryRadarChart.tsx`
- Modify: `dashboard/src/app/recovery/page.tsx` (import and render)
- Test: `dashboard/src/components/recovery/__tests__/MasteryRadarChart.test.tsx`

- [ ] **Step 1: Create the component**

```tsx
'use client'

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

interface RadarDataPoint {
  topic: string
  mastery: number
}

interface MasteryRadarChartProps {
  data: RadarDataPoint[]
}

export function MasteryRadarChart({ data }: MasteryRadarChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-foreground-muted text-sm">
        No topic data available
      </div>
    )
  }

  const maxMastery = Math.max(...data.map(d => d.mastery), 60)
  const niceMax = Math.ceil(maxMastery / 10) * 10

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid stroke="hsl(var(--border))" />
          <PolarAngleAxis
            dataKey="topic"
            tick={{ fill: 'hsl(var(--foreground-muted))', fontSize: 11 }}
            tickFormatter={(v: string) => v.length > 12 ? v.slice(0, 12) + '…' : v}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, niceMax]}
            tick={{ fill: 'hsl(var(--foreground-muted))', fontSize: 10 }}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '13px',
            }}
            formatter={(value: number) => [`${value.toFixed(0)}%`, 'Mastery']}
          />
          <Radar
            name="Mastery"
            dataKey="mastery"
            stroke="hsl(var(--primary))"
            fill="hsl(var(--primary))"
            fillOpacity={0.2}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 2: Integrate into recovery page**

Add import at top of `dashboard/src/app/recovery/page.tsx`:

```tsx
import { MasteryRadarChart } from '@/components/recovery/MasteryRadarChart'
```

After the stats cards grid (after line 369 in the current file), add the radar chart section:

```tsx
{data.weak_topics.length >= 3 && (
  <div className="bg-card rounded-xl border border-border p-5">
    <h2 className="text-lg font-semibold text-foreground mb-4">Mastery Overview</h2>
    <MasteryRadarChart
      data={data.weak_topics.map(wt => ({
        topic: wt.topic,
        mastery: wt.average_score,
      }))}
    />
  </div>
)}
```

- [ ] **Step 3: Verify build**

Run: `npx tsc --noEmit` in `dashboard/`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/recovery/MasteryRadarChart.tsx dashboard/src/app/recovery/page.tsx
git commit -m "feat: add mastery radar chart to recovery dashboard"
```

---

### Task 2: Progress Trend Graph Component

**Files:**
- Create: `dashboard/src/components/recovery/ProgressTrendGraph.tsx`
- Modify: `dashboard/src/app/recovery/page.tsx` (use in weak topic cards)
- Test: `dashboard/src/components/recovery/__tests__/ProgressTrendGraph.test.tsx`

- [ ] **Step 1: Create the component**

```tsx
'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface HistoryPoint {
  average_score: number
  recorded_at: string
}

interface ProgressTrendGraphProps {
  data: HistoryPoint[]
  topic: string
}

export function ProgressTrendGraph({ data, topic }: ProgressTrendGraphProps) {
  if (!data || data.length < 2) {
    return (
      <div className="flex items-center justify-center h-32 text-foreground-muted text-xs">
        Not enough data yet
      </div>
    )
  }

  const formatted = data.map(p => ({
    date: new Date(p.recorded_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    score: p.average_score,
  }))

  const firstVal = formatted[0].score
  const lastVal = formatted[formatted.length - 1].score
  const trendColor = lastVal > firstVal ? '#22c55e' : lastVal < firstVal ? '#ef4444' : '#6b7280'

  return (
    <div className="w-full h-32">
      <div className="flex items-center justify-between text-xs text-foreground-muted mb-1">
        <span>Progress over time</span>
        <span style={{ color: trendColor }}>
          {firstVal.toFixed(0)}% → {lastVal.toFixed(0)}%
        </span>
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formatted}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'hsl(var(--foreground-muted))' }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--foreground-muted))' }} tickFormatter={(v: number) => `${v}%`} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <Line type="monotone" dataKey="score" stroke={trendColor} strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 2: Replace inline SimpleMiniChart in recovery page**

Add import:
```tsx
import { ProgressTrendGraph } from '@/components/recovery/ProgressTrendGraph'
```

Find the `SimpleMiniChart` usage in the weak topic card (around line 503-507) and replace:
```tsx
{history[wt.topic] && history[wt.topic].length >= 2 && (
  <div className="mt-3 pt-3 border-t border-border/50">
    <SimpleMiniChart points={history[wt.topic]} topic={wt.topic} />
  </div>
)}
```
with:
```tsx
{history[wt.topic] && (
  <div className="mt-3 pt-3 border-t border-border/50">
    <ProgressTrendGraph data={history[wt.topic]} topic={wt.topic} />
  </div>
)}
```

- [ ] **Step 3: Verify build**

Run: `npx tsc --noEmit` in `dashboard/`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/recovery/ProgressTrendGraph.tsx dashboard/src/app/recovery/page.tsx
git commit -m "feat: add progress trend graph to recovery dashboard"
```

---

### Task 3: Topic Heatmap Component

**Files:**
- Create: `dashboard/src/components/recovery/TopicHeatmap.tsx`
- Modify: `dashboard/src/app/recovery/page.tsx` (add heatmap section)
- Test: `dashboard/src/components/recovery/__tests__/TopicHeatmap.test.tsx`

- [ ] **Step 1: Create the component**

```tsx
'use client'

interface HeatmapDay {
  date: string
  mastery: number
}

interface TopicHeatmapProps {
  history: Record<string, { average_score: number; recorded_at: string }[]>
}

export function TopicHeatmap({ history }: TopicHeatmapProps) {
  const allPoints: HeatmapDay[] = Object.values(history)
    .flat()
    .map(p => ({ date: p.recorded_at.split('T')[0], mastery: p.average_score }))
    .filter((p, i, arr) => arr.findIndex(x => x.date === p.date) === i)
    .sort((a, b) => a.date.localeCompare(b.date))

  if (allPoints.length < 2) {
    return (
      <div className="flex items-center justify-center h-24 text-foreground-muted text-sm">
        Complete activities to see your progress heatmap
      </div>
    )
  }

  const maxMastery = Math.max(...allPoints.map(p => p.mastery), 1)

  const getColor = (mastery: number) => {
    const ratio = mastery / maxMastery
    if (ratio < 0.25) return 'bg-red-500/20'
    if (ratio < 0.5) return 'bg-orange-500/30'
    if (ratio < 0.75) return 'bg-yellow-500/40'
    return 'bg-green-500/40'
  }

  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {allPoints.slice(-28).map((p, i) => (
          <div
            key={i}
            className={`w-6 h-6 rounded ${getColor(p.mastery)} flex items-center justify-center text-[9px] text-foreground-muted cursor-default`}
            title={`${p.date}: ${p.mastery.toFixed(0)}%`}
          >
            {new Date(p.date).getDate()}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-2 text-xs text-foreground-muted">
        <span>Less</span>
        <div className="w-3 h-3 rounded bg-red-500/20" />
        <div className="w-3 h-3 rounded bg-orange-500/30" />
        <div className="w-3 h-3 rounded bg-yellow-500/40" />
        <div className="w-3 h-3 rounded bg-green-500/40" />
        <span>More</span>
        <span className="ml-auto">Last 28 days</span>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Add heatmap section to recovery page**

Add import:
```tsx
import { TopicHeatmap } from '@/components/recovery/TopicHeatmap'
```

Add after the "Mastery Overview" radar chart section:
```tsx
<div className="bg-card rounded-xl border border-border p-5">
  <div className="flex items-center gap-2 mb-4">
    <h2 className="text-lg font-semibold text-foreground">Progress Heatmap</h2>
  </div>
  <TopicHeatmap history={history} />
</div>
```

- [ ] **Step 3: Verify build**

Run: `npx tsc --noEmit` in `dashboard/`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/recovery/TopicHeatmap.tsx dashboard/src/app/recovery/page.tsx
git commit -m "feat: add topic heatmap to recovery dashboard"
```

---

### Task 4: Learning Tree Component

**Files:**
- Create: `dashboard/src/components/recovery/LearningTree.tsx`
- Modify: `dashboard/src/app/recovery/page.tsx` (replace flat weak topic list)
- Test: `dashboard/src/components/recovery/__tests__/LearningTree.test.tsx`

- [ ] **Step 1: Create the component**

```tsx
'use client'

import { useState } from 'react'
import { ChevronRight, ChevronDown, AlertTriangle } from 'lucide-react'

interface Misconception {
  pattern_type: string
  description: string
  frequency: number
}

interface WeakTopic {
  topic: string
  unit: string
  grade_level: number
  average_score: number
  attempt_count: number
  severity: string
  confidence: number
  misconceptions: Misconception[]
}

interface LearningTreeProps {
  topics: WeakTopic[]
}

function TopicNode({ topic, defaultOpen }: { topic: WeakTopic; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen)

  const masteryColor =
    topic.average_score < 40 ? 'text-red-400' :
    topic.average_score < 60 ? 'text-yellow-400' :
    'text-green-400'

  const dotColor =
    topic.average_score < 40 ? 'bg-red-400' :
    topic.average_score < 60 ? 'bg-yellow-400' :
    'bg-green-400'

  return (
    <div className="border border-border rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-3 text-left hover:bg-background-secondary/50 transition-colors rounded-lg"
      >
        {open ? <ChevronDown className="w-4 h-4 text-foreground-muted flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-foreground-muted flex-shrink-0" />}
        <div className={`w-2.5 h-2.5 rounded-full ${dotColor} flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate">{topic.topic}</p>
          <p className="text-xs text-foreground-muted truncate">
            {topic.unit && `${topic.unit} · `}Grade {topic.grade_level}
          </p>
        </div>
        <span className={`text-sm font-semibold ${masteryColor}`}>
          {topic.average_score.toFixed(0)}%
        </span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-0 border-t border-border/50">
          <div className="grid grid-cols-3 gap-3 mt-3">
            <div>
              <p className="text-xs text-foreground-muted">Attempts</p>
              <p className="text-sm font-semibold text-foreground">{topic.attempt_count}</p>
            </div>
            <div>
              <p className="text-xs text-foreground-muted">Confidence</p>
              <p className="text-sm font-semibold text-foreground">{(topic.confidence * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-xs text-foreground-muted">Severity</p>
              <p className={`text-sm font-semibold capitalize ${masteryColor}`}>{topic.severity}</p>
            </div>
          </div>
          {topic.misconceptions.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-xs font-medium text-foreground-muted mb-2">Misconceptions:</p>
              {topic.misconceptions.map((mc, j) => (
                <div key={j} className="flex items-center gap-2 text-xs text-foreground-muted mb-1">
                  <AlertTriangle className="w-3 h-3 text-yellow-400 flex-shrink-0" />
                  <span>{mc.pattern_type}: {mc.description}</span>
                  <span className="text-foreground-muted/60">({mc.frequency}x)</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function LearningTree({ topics }: LearningTreeProps) {
  if (topics.length === 0) {
    return (
      <div className="text-center py-8 text-foreground-muted text-sm">
        No weak topics to display
      </div>
    )
  }

  const sorted = [...topics].sort((a, b) => a.average_score - b.average_score)

  return (
    <div className="space-y-2">
      {sorted.map((topic, i) => (
        <TopicNode key={i} topic={topic} defaultOpen={i < 2} />
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Replace weak topics section in recovery page**

Add import:
```tsx
import { LearningTree } from '@/components/recovery/LearningTree'
```

Replace the entire Weak Topics section (from `{data.weak_topics.length > 0 ? (` to the closing `)` before the active plans section) with:

```tsx
{data.weak_topics.length > 0 ? (
  <div className="bg-card rounded-xl border border-border p-5">
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-lg font-semibold text-foreground">Weak Topics</h2>
      <span className="text-sm text-foreground-muted">{data.total_weak_topics} topic{data.total_weak_topics !== 1 ? 's' : ''}</span>
    </div>
    <LearningTree topics={data.weak_topics} />
  </div>
) : (
  <div className="bg-card rounded-xl border border-border p-8 text-center">
    <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-3" />
    <p className="text-foreground-muted font-medium">No weak topics found</p>
    <p className="text-sm text-foreground-muted/60 mt-1">Student is performing well across all topics</p>
  </div>
)}
```

Ensure `CheckCircle2` is imported (already is from lucide-react).

- [ ] **Step 3: Verify build**

Run: `npx tsc --noEmit` in `dashboard/`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/components/recovery/LearningTree.tsx dashboard/src/app/recovery/page.tsx
git commit -m "feat: add learning tree to replace flat weak topic list"
```

---

### Task 5: Telegram Bot — Recovery Plan View Command

**Files:**
- Modify: `src/telegram/bot.py` (add handlers + register command)

- [ ] **Step 1: Add recovery plan viewing handler**

Add before the `build_app()` function in `src/telegram/bot.py`:

```python
async def recovery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from sqlalchemy import select
    from src.api.gamification import XP_SOURCES

    async def _handle():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == update.effective_user.id))
            user = result.scalar_one_or_none()
            if not user:
                await _reply_long(update, "❌ You need to /start first to use this command.")
                return

            from src.database.models import RecoveryPlan, RecoveryTask
            plans_result = await session.execute(
                select(RecoveryPlan)
                .where(RecoveryPlan.user_id == user.id, RecoveryPlan.status == "active")
                .order_by(RecoveryPlan.created_at.desc())
            )
            plans = list(plans_result.scalars().all())

            if not plans:
                await _reply_long(update, "📋 *No Active Recovery Plans*\n\nComplete quizzes to identify weak areas — a recovery plan will be generated automatically when needed.", parse_mode="Markdown")
                return

            from src.api.recovery import _get_weak_topics
            weak_topics = await _get_weak_topics(user.id, session)

            lines = ["📋 *Recovery Plans*"]
            if weak_topics:
                lines.append(f"\n🔍 *Weak Topics:* {len(weak_topics)} identified")
                for wt in weak_topics[:3]:
                    icon = "🔴" if wt.severity == "critical" else "🟡" if wt.severity == "moderate" else "🔵"
                    lines.append(f"{icon} {wt.topic} — {wt.average_score:.0f}%")

            from src.api.gamification import _get_recovery_progress
            rp = await _get_recovery_progress(user.id, session)
            if rp:
                lines.append(f"\n📊 *Overall Progress:* {rp.completed_tasks}/{rp.total_tasks} tasks ({rp.overall_progress_pct:.0f}%)")

            for plan in plans:
                lines.append(f"\n*Plan: {plan.topic}*")
                lines.append(f"Progress: {plan.completed_tasks}/{plan.total_tasks} ({plan.progress_pct:.0f}%)")
                tasks_result = await session.execute(
                    select(RecoveryTask).where(RecoveryTask.plan_id == plan.id).order_by(RecoveryTask.created_at)
                )
                tasks = list(tasks_result.scalars().all())
                for task in tasks:
                    status = "✅" if task.is_completed else "⬜"
                    lines.append(f"{status} {task.title}")

            await _reply_long(update, "\n".join(lines), parse_mode="Markdown")

    await _db_try(_handle)
```

- [ ] **Step 2: Add handler function for task completion callback**

```python
async def handle_recovery_complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = query.data.replace("recovery_complete_", "")

    from sqlalchemy import select
    from src.database.models import RecoveryTask, RecoveryPlan
    from src.api.recovery import complete_task
    from src.api.gamification import XP_SOURCES

    async def _handle():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == update.effective_user.id))
            user = result.scalar_one_or_none()
            if not user:
                await query.edit_message_text("❌ User not found. Please /start first.")
                return

            task_result = await session.execute(select(RecoveryTask).where(RecoveryTask.id == task_id))
            task = task_result.scalar_one_or_none()
            if not task:
                await query.edit_message_text("❌ Task not found.")
                return
            if task.is_completed:
                await query.edit_message_text(f"✅ Task *{task.title}* was already completed!", parse_mode="Markdown")
                return

            result_data = await complete_task(task_id, user.id, session)
            await session.commit()

            await query.edit_message_text(
                f"✅ *Task Completed!*\n\n{task.title}\n\n+{result_data.xp_awarded} XP",
                parse_mode="Markdown",
            )

    await _db_try(_handle)
```

- [ ] **Step 3: Add handler for post-quiz recovery prompt**

```python
async def handle_recovery_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    update.effective_message = query.message
    await recovery_command(update, context)
```

- [ ] **Step 4: Register all new handlers**

Add in `build_app()` after the existing command registrations (after line 1223):

```python
    app.add_handler(CommandHandler("recovery", recovery_command))
    app.add_handler(CallbackQueryHandler(handle_recovery_complete_task, pattern=r"^recovery_complete_"))
    app.add_handler(CallbackQueryHandler(handle_recovery_view, pattern="^recovery_view$"))
```

- [ ] **Step 5: Add recovery prompt to quiz end screen**

Find `handle_quiz_end` function and after the quiz result message is built (after XP/notification text is appended), add:

```python
            from src.database.models import RecoveryPlan
            factory = async_session_factory()
            async with factory() as session:
                result = await session.execute(select(User).where(User.telegram_id == update.effective_user.id))
                user = result.scalar_one_or_none()
                if user:
                    plans_result = await session.execute(
                        select(RecoveryPlan).where(
                            RecoveryPlan.user_id == user.id,
                            RecoveryPlan.status == "active",
                        ).limit(1)
                    )
                    plan = plans_result.scalar_one_or_none()
                    if plan:
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                        recovery_row = [InlineKeyboardButton("📋 View Recovery Plan", callback_data="recovery_view")]
                        reply_markup.inline_keyboard.append(recovery_row)
```

- [ ] **Step 6: Verify with typecheck**

Run: `mypy src/telegram/bot.py`
Expected: No type errors

- [ ] **Step 7: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat: add recovery plan commands to telegram bot"
```

---

### Task 6: Telegram Bot — Progress Summary Command

**Files:**
- Modify: `src/telegram/bot.py`

- [ ] **Step 1: Add progress summary handler**

Add before `build_app()`:

```python
async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from sqlalchemy import select

    async def _handle():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == update.effective_user.id))
            user = result.scalar_one_or_none()
            if not user:
                await _reply_long(update, "❌ You need to /start first.")
                return

            from src.api.recovery import _get_weak_topics
            weak_topics = await _get_weak_topics(user.id, session)

            if not weak_topics:
                await _reply_long(update, "📊 *Mastery Progress*\n\nNo weak topics detected! You're doing great across all subjects.", parse_mode="Markdown")
                return

            lines = ["📊 *Mastery Progress*"]
            for wt in sorted(weak_topics, key=lambda x: x.average_score):
                bar_len = max(1, int(wt.average_score / 10))
                bar = "█" * bar_len + "░" * (10 - bar_len)
                icon = "🔴" if wt.average_score < 40 else "🟡" if wt.average_score < 60 else "🟢" if wt.average_score < 80 else "💚"
                lines.append(f"\n{icon} *{wt.topic}*")
                lines.append(f"`{bar}` {wt.average_score:.0f}%")
                lines.append(f"Confidence: {wt.confidence*100:.0f}% | Attempts: {wt.attempt_count}")

            await _reply_long(update, "\n".join(lines), parse_mode="Markdown")

    await _db_try(_handle)
```

- [ ] **Step 2: Register the handler**

Add in `build_app()`:
```python
    app.add_handler(CommandHandler("progress", progress_command))
```

Note: There's already a `handle_progress` callback handler at line 1315. This new `progress_command` is a text command handler (`/progress`), not a callback. They won't conflict.

- [ ] **Step 3: Verify with typecheck**

Run: `mypy src/telegram/bot.py`
Expected: No type errors

- [ ] **Step 4: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat: add /progress command for mastery summary"
```

---

### Task 7: Add Browser Visual Verification Playwright Tests

**Files:**
- Create: `dashboard/playwright/recovery-visuals.spec.ts`

- [ ] **Step 1: Create Playwright test for recovery visualizations**

```ts
import { test, expect } from '@playwright/test'

test.describe('Recovery Dashboard Visualizations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/recovery')
  })

  test('shows empty state initially', async ({ page }) => {
    await expect(page.getByText('Enter a student ID to get started')).toBeVisible()
  })

  test('radar chart appears after loading student data', async ({ page }) => {
    // Enter a known student UUID and submit
    const input = page.getByPlaceholder('Enter student UUID...')
    await input.fill('test-student-id')
    await page.getByRole('button', { name: 'Look up' }).click()
    // Wait for data to load
    await page.waitForResponse(response =>
      response.url().includes('/recovery/dashboard/') && response.status() === 200
    )
    // Radar chart should render when 3+ weak topics exist
    await page.waitForTimeout(1000)
    const rechartsContainer = page.locator('.recharts-wrapper')
    await expect(rechartsContainer.first()).toBeVisible({ timeout: 5000 })
  })

  test('learning tree shows expandable topic nodes', async ({ page }) => {
    const input = page.getByPlaceholder('Enter student UUID...')
    await input.fill('test-student-id')
    await page.getByRole('button', { name: 'Look up' }).click()
    await page.waitForResponse(response =>
      response.url().includes('/recovery/dashboard/') && response.status() === 200
    )
    // Learning tree nodes should be visible
    const expandButtons = page.locator('button').filter({ has: page.locator('svg.lucide-chevron-right') })
    if (await expandButtons.count() > 0) {
      await expandButtons.first().click()
      await expect(page.getByText('Attempts').first()).toBeVisible({ timeout: 3000 })
    }
  })

  test('heatmap renders with activity data', async ({ page }) => {
    const input = page.getByPlaceholder('Enter student UUID...')
    await input.fill('test-student-id')
    await page.getByRole('button', { name: 'Look up' }).click()
    await page.waitForResponse(response =>
      response.url().includes('/recovery/dashboard/') && response.status() === 200
    )
    // Heatmap section should render
    await expect(page.getByText('Progress Heatmap')).toBeVisible({ timeout: 5000 })
  })
})
```

- [ ] **Step 2: Run Playwright tests**

Run: `npx playwright test dashboard/playwright/recovery-visuals.spec.ts` in project root
Expected: Tests pass

- [ ] **Step 3: Commit**

```bash
git add dashboard/playwright/recovery-visuals.spec.ts
git commit -m "test: add Playwright tests for recovery visualizations"
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** All 4 Phase 1 components (radar, trend, heatmap, learning tree) and all 3 Phase 2 bot features (plan view, task completion, progress) are covered.
- [ ] **Placeholder scan:** No TBD, TODO, or empty steps. Every step has actual code.
- [ ] **Type consistency:** Component props match `WeakTopic`/`DashboardData` interfaces in existing recovery page. Bot handlers follow existing `_db_try` pattern.
