# Recovery Plan Enhancements

## Overview

Four enhancement phases building on the existing recovery plan system to add mastery visualizations, Telegram bot integration, push notifications, and an adaptive quiz engine.

## Execution Strategy: Two Batches

**Batch 1** (PRD: `ralph/recovery-visuals-bot`) — Phases 1 + 2, pure UI/bot work, no schema changes.
**Batch 2** (PRD: `ralph/recovery-notifications-adaptive`) — Phases 3 + 4, infrastructure + ML.

---

## Phase 1 — Mastery Visualizations

### Components

| Component | Type | Data Source | Description |
|-----------|------|-------------|-------------|
| `MasteryRadarChart` | Recharts `RadarChart` | `GET /recovery/dashboard/{id}` → `weak_topics[].mastery_score` | Spider chart comparing mastery across all topics |
| `TopicHeatmap` | Custom CSS grid | `GET /recovery/history/{id}/{topic}` → mastery over time | Calendar-style view of mastery changes |
| `ProgressTrendGraph` | Recharts `LineChart` | `GET /recovery/history/{id}/{topic}` | Line chart per topic showing mastery trend |
| `LearningTree` | Recursive component | `weak_topics` + subtopic data | Hierarchical topic tree with mastery color coding |

### Integration

All components mount on the existing `/recovery` dashboard page. Placement per section:
- Radar chart at top (overall snapshot)
- Learning tree in the Weak Topics section replacing plain list
- Trend graph in each weak topic card
- Heatmap as a new panel below active plans

### Library

Recharts is already available in the dashboard — confirmed via `package.json`. No new dependencies needed.

---

## Phase 2 — Telegram Bot Enhancements

### New Bot Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `/recovery` | `_handle_recovery(user_id)` | Shows active plan with task list, weak topics, progress % |
| `/complete <task_id>` | `_complete_task(user_id, task_id)` | Mark task done from chat, returns XP + updated progress |
| `/progress` | `_handle_progress(user_id)` | Text summary of topic mastery with sparkline-style bars |

### Inline Buttons

| Button | Trigger | Action |
|--------|---------|--------|
| "View Recovery Plan" | After quiz score < 60% | Sends `/recovery` output |
| "Complete Task" | Per task in plan view | Marks task complete, refreshes plan view |
| "📊 Progress" | In plan view | Sends `/progress` output |

### Backend Changes

- Add `_user_by_telegram_id()` helper (exists as pattern in `_save_quiz_rewards`)
- Add `_format_plan_text()` and `_format_progress_text()` formatters
- Inline keyboard handlers for task completion confirmations

---

## Phase 3 — Push Notifications

### New Models

```python
class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), primary_key=True)
    email: Mapped[str]
    email_verified: Mapped[bool] = mapped_column(default=False)
    digest_frequency: Mapped[str]  # "daily" | "weekly" | "never"
    milestone_alerts: Mapped[bool] = mapped_column(default=True)
```

### Email Templates (Jinja2)

- `milestone_alert.html` — "You improved 18% in Cell Biology!"
- `daily_digest.html` — Summary of today's mastery changes, due reviews, recommendations
- `weekly_digest.html` — Broader weekly progress summary
- `review_reminder.html` — "You have 3 topics due for review"

### Delivery

- `smtplib` (stdlib) for sending, configurable via `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASS` env vars
- Queue-based: notifications batch every hour via a lightweight scheduler (`scripts/send_notifications.py`)
- No external service dependency — works with any SMTP server

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/notifications/preferences/{user_id}` | GET | Read current preferences |
| `/notifications/preferences/{user_id}` | PUT | Save email + frequency |
| `/notifications/preferences/{user_id}/verify` | POST | Send verification code |
| `/notifications/preferences/{user_id}/verify/{code}` | POST | Confirm verification code |

### Scheduler

Cron-compatible `scripts/send_digests.py` — callable from system cron or APScheduler. Checks due reviews and batches email digests.

---

## Phase 4 — Adaptive Quiz Engine

### New Models

```python
class QuestionAttempt(Base):
    __tablename__ = "question_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"))
    question_id: Mapped[str]
    topic: Mapped[str]
    correct: Mapped[bool]
    time_spent: Mapped[float]  # seconds
    hints_used: Mapped[int]
    attempt_number: Mapped[int]  # per question
    created_at: Mapped[datetime]

class StudentAbility(Base):
    __tablename__ = "student_abilities"
    user_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.user_id"), primary_key=True)
    topic: Mapped[str] = mapped_column(primary_key=True)
    ability_score: Mapped[float]  # IRT theta
    uncertainty: Mapped[float]  # standard error
    attempt_count: Mapped[int]
    updated_at: Mapped[datetime]
```

### IRT Implementation

Simple 1-parameter Rasch model:
- Estimate student ability per topic using maximum likelihood estimation
- Track question difficulty as a property on each question
- Select questions with difficulty closest to `ability + 0.5` (slightly challenging)
- Update ability estimate after each quiz using observed correct/incorrect + difficulty

### Adaptive Question Selection

```python
def select_next_question(user_id: int, topic: str, session: Session) -> Question:
    ability = get_ability(user_id, topic, session)
    available = get_unanswered_questions(topic, session)
    if not available:
        return random_question(topic, session)
    target_difficulty = ability + 0.5
    return min(available, key=lambda q: abs(q.difficulty - target_difficulty))
```

### Question Model Changes

Add `difficulty_score: Float = 0.0` column to existing `Question` model. Migrate existing string difficulties:
- `"easy"` → `-1.0`
- `"medium"` → `0.0`
- `"hard"` → `1.0`

New questions default to `0.0` (medium) until enough attempt data accumulates to estimate true difficulty.

### Integration

- Wrap existing `QuizAgent` with adaptive selector
- Students with < 5 attempts per topic use current random selection (cold start)

---

## User Stories (Batch 1)

### RP-VIS-001 — Mastery Radar Chart

As a student, I want a radar chart showing my mastery across all biology topics so I can see strengths and weaknesses at a glance.

- Add Recharts `RadarChart` to the `/recovery` page
- Data sourced from `weak_topics[].mastery_score`
- One axis per topic, fill color scales from red to green
- Typecheck passes
- Verify in browser using Playwright browser tools

### RP-VIS-002 — Progress Trend Graphs

As a student, I want a line chart per topic showing my mastery trend over time so I can see improvement.

- Recharts `LineChart` in each weak topic card
- Data from `GET /recovery/history/{user_id}/{topic}`
- X-axis: date, Y-axis: mastery %
- Flat/default state with "Not enough data yet" message when history < 2 points
- Typecheck passes
- Verify in browser using Playwright browser tools

### RP-VIS-003 — Topic Heatmap

As a student, I want a calendar heatmap showing my mastery changes over time.

- Custom CSS grid component showing mastery % as color intensity per day
- Placed below active plans in `/recovery`
- Empty state: gray grid with "Complete activities to see your progress heatmap"
- Typecheck passes
- Verify in browser using Playwright browser tools

### RP-VIS-004 — Learning Tree View

As a student, I want a hierarchical topic tree with mastery color coding so I can navigate subtopics.

- Recursive component rendering topic → subtopic hierarchy
- Mastery % shown as color-coded dot (red < 40%, yellow < 60%, green >= 60%)
- Expandable/collapsible subtopic nodes
- Replaces flat weak topic list in the Weak Topics section
- Typecheck passes
- Verify in browser using Playwright browser tools

### RP-BOT-001 — Telegram Plan View

As a student, I want to view my recovery plan from Telegram.

- `/recovery` command shows active plan with status emoji per task
- Shows progress % and weak topics summary
- Uses `_reply_long()` for splitting long plan texts
- Inline "Complete Task" button per task
- Typecheck passes

### RP-BOT-002 — Telegram Task Completion

As a student, I want to complete recovery tasks directly from Telegram chat.

- `callback_data` handlers for task completion buttons
- Calls existing `POST /recovery/task/complete` endpoint
- Replies with updated plan + XP awarded
- Error handling for already-completed tasks
- Typecheck passes

### RP-BOT-003 — Post-Quiz Recovery Prompt

As a student, I want to see a "View Recovery Plan" button after scoring low on a quiz.

- Button appears in quiz result message when score < 60%
- Calls `/recovery` handler on tap
- Existing callback pattern `^quiz$` matches quiz result screen
- Typecheck passes

---

## User Stories (Batch 2)

### RP-NOT-001 — Notification Preferences

As a student, I want to set my email and notification preferences for recovery updates.

- New DB table: `notification_preferences`
- PUT/POST endpoints for saving email, frequency, opt-in
- Email verification via confirmation code
- Typecheck passes

### RP-NOT-002 — Milestone Email Alerts

As a student, I want email alerts when I reach a recovery milestone.

- Check mastery improvements after each task/quiz completion
- Send email for significant improvements (>= 10% mastery increase)
- Jinja2 template with personalized improvement stats
- Typecheck passes

### RP-NOT-003 — Daily/Weekly Digests

As a student, I want periodic email digests summarizing my progress.

- Daily digest: recent mastery changes, due reviews, recommendations
- Weekly digest: broader summary with trend highlights
- Script `scripts/send_digests.py` for cron-based execution
- Typecheck passes

### RP-NOT-004 — Review Reminder Emails

As a student, I want email reminders when spaced repetition reviews are due.

- Check `spaced_repetition_schedule` for due items
- Send reminder email listing topics due for review
- Typecheck passes

### RP-ADP-001 — Question Attempt Tracking

As a developer, I want to track each quiz question attempt with correctness and timing.

- New DB table: `question_attempts`
- Record attempt data during quiz submission
- Data used for IRT ability estimation
- Typecheck passes

### RP-ADP-002 — Student Ability Estimation

As a developer, I want to estimate student ability per topic using IRT.

- New DB table: `student_abilities`
- Implement Rasch model ability estimation
- Update after each quiz completion
- Cold start: default ability = 0.0, fall back to random selection
- Typecheck passes

### RP-ADP-003 — Adaptive Question Selection

As a student, I want quiz questions selected to match my ability level.

- Integrate adaptive selector into `QuizAgent`
- Pick questions at `difficulty ≈ ability + 0.5`
- Fall back to random for students with insufficient data
- Typecheck passes
- Verify in browser using Playwright browser tools
