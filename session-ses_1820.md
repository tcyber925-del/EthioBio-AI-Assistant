
Here's a summary of each domain's data model:

---

### 1. Quiz Results

**`QuizAttempt`** (`models.py:166`) — stores each quiz submission.
| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | FK → `users.id` | |
| `quiz_id` | FK → `quizzes.id` | |
| `score` | Float | nullable (set on completion) |
| `total` | Integer | question count |
| `answers` | JSON | list of answer dicts |
| `completed` | Boolean | default False |
| `started_at` / `completed_at` | DateTime | |

**`QuestionAttempt`** (`models.py:477`) — per-question granular data for adaptive engine.
| Field | Type |
|---|---|
| `id` UUID PK, `user_id`, `question_id`, `quiz_id` (nullable) | FKs |
| `correct` | Boolean |
| `time_spent` | Float? |
| `hints_used` | int (default 0) |
| `attempt_number` | int (auto-increments per user+question) |

**`Question`** (`models.py:130`) — has `difficulty_score` (Float, -1.0 to 1.0) for IRT usage.

**Pydantic:** `QuizSubmitRequest` / `QuizSubmitResponse` → includes `score`, `total`, `correct`, `feedback`, `xp_awarded`, `recommendations`.

---

### 2. Mastery Tracking

**`StudentMastery`** (`models.py:350`) — per-user, per-topic mastery snapshot.
| Field | Type | Notes |
|---|---|---|
| `user_id` | FK → `users.id` | |
| `topic` | String(300) | |
| `grade_level` | Integer | |
| `average_score` | Float | computed from attempts |
| `attempt_count`, `total_questions_attempted`, `correct_answers` | Integer | |
| `severity` | String(20) | computed: `critical` <40%, `moderate` <60%, `mild` <80%, `good` ≥80% |
| `confidence` | Float | computed as `min(attempt_count / 3, 1.0)` |

**`StudentAbility`** (`models.py:493`) — Bayesian IRT estimates per user+topic.
| Field | Type |
|---|---|
| `user_id` + `topic` | composite PK |
| `ability_score` | Float (logit-scaled, default 0.0) |
| `uncertainty` | Float (default 3.0) |
| `attempt_count` | Integer |

**`TopicMasteryHistory`** (`models.py:391`) — time-series snapshots of mastery changes with `source` (e.g. `"quiz"`, `"task_completion"`) and `source_id`.

**`MisconceptionPattern`** (`models.py:371`) — tracks repeated wrong answers per user+topic: `pattern_type`, `frequency`, `common_wrong_answer`, `related_question_ids` (JSON list).

**Pydantic:** `WeakTopicDetail` (topic, unit, grade_level, average_score, severity, confidence, misconceptions), `MasteryHistoryPoint`/`MasteryHistoryResponse`.

---

### 3. Recovery Plans

**`RecoveryPlan`** (`models.py:285`)
| Field | Type |
|---|---|
| `user_id` (FK), `topic` | |
| `total_tasks` / `completed_tasks` | Integer |
| `status` | String(20): `"active"` or `"completed"` |

**`RecoveryTask`** (`models.py:301`)
| Field | Type |
|---|---|
| `plan_id` FK → `recovery_plans.id` | |
| `title`, `task_type` | String |
| `is_completed` | Boolean (default False) |
| `xp_awarded` | Integer (default 0) |

**`RecoveryNotification`** (`models.py:430`) — events like `mastery_improvement`, `severity_upgrade`, `plan_completed` with `improvement_pct`, `old_value`, `new_value`.

**Pydantic:** `CompleteTaskResponse` — returns `xp_awarded`, `milestone_bonus`, `total_xp`, `level_up`, `new_level`, `plan_completed`, `progress_pct`.

**XP constants** (in `gamification.py`): `recovery_task_completion: 40`, milestone bonuses at 3/5/10/15 tasks completed.

---

### 4. Spaced Repetition Progress

**`SpacedRepetitionSchedule`** (`models.py:410`)
| Field | Type | Notes |
|---|---|---|
| `user_id` FK, `topic`, `unit`?, `grade_level` | |
| `mastery_score` | Float | |
| `interval_days` | Integer | default 1 |
| `ease_factor` | Float | default 2.5, clamped [1.3, 3.0] |
| `next_review_at` | DateTime | |
| `last_reviewed_at` | DateTime? | |
| `review_count` | Integer | default 0 |

**Constants** (`spaced_repetition.py`): `MIN_EASE_FACTOR=1.3`, `MAX_EASE_FACTOR=3.0`, `INITIAL_INTERVALS = {"critical": 1, "moderate": 2, "mild": 3, "good": 7}`.

**Pydantic:** `SpacedRepetitionItem` (includes computed `is_due`, `days_overdue`), `SpacedRepetitionReviewRequest` (user_id, topic, new_score), `DueReviewsResponse`.

---

### 5. User Profiles

**`User`** (`models.py:38`)
| Field | Type |
|---|---|
| `id` UUID PK | |
| `telegram_id` | BigInteger, unique, nullable |
| `phone` | String(20), unique, nullable |
| `role` | Enum: `student`, `teacher`, `admin`, `parent` |
| `language_preference` | String(10), default `"en"` |
| `grade_level` | Integer, nullable |

**`StudentProfile`** (`models.py:58`) — 1:1 with User.
| Field | Type | Notes |
|---|---|---|
| `school`, `region` | String?, ? | |
| `topic_mastery` | JSON dict | per-topic mastery snapshot |
| `score_history` | JSON list | |
| `weak_areas` | JSON list of strings | |

**`UserGamification`** (`models.py:242`) — 1:1 with User: `total_xp`, `level`, `current_streak`, `longest_streak`, `last_active_date`.

**`NotificationPreference`** (`models.py:566`) — PK is `user_id` (1:1): `email`, `email_verified`, `digest_frequency`, `milestone_alerts`, `review_reminders`, verification fields.

**Pydantic:** `GamificationProfileResponse` — bundles `total_xp`, `level`, `streak`, `recent_events`, `achievements`, `recovery_progress`, etc.

---

**Key relationships flow:** `User` 1:1 `StudentProfile` / `UserGamification` / `NotificationPreference`; 1:M `QuizAttempt` / `StudentMastery` / `RecoveryPlan` / `SpacedRepetitionSchedule` / `StudentAbility` (composite PK with topic). Mastery is computed on quiz submit (`analyze_quiz_attempt()` → updates `StudentMastery`, creates `TopicMasteryHistory` snapshot, detects `MisconceptionPattern`, syncs `StudentProfile.weak_areas`). Spaced repetition is separate but uses same `topic` key for cross-referencing.

---

