# Recovery Plan Enhancements — Batch 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add push notifications (email) and an adaptive quiz engine (IRT-based) to the recovery plan system.

**Architecture:** Phase 3 adds DB model, email service, Jinja2 templates, and a cron script. Phase 4 adds DB models for attempt tracking and ability estimation, a Rasch IRT implementation, and integrates adaptive question selection into the QuizAgent.

**Tech Stack:** Python smtplib (stdlib), Jinja2 (already in deps), APScheduler or cron, FastAPI, SQLAlchemy async

---

### Task 1: Notification Preferences Model and API

**Files:**
- Modify: `src/database/models.py` (add NotificationPreference model)
- Create: `src/api/notifications.py` (preferences CRUD endpoints)
- Modify: `src/main.py` (register router)

- [ ] **Step 1: Add NotificationPreference model**

Add to `src/database/models.py` after existing models:

```python
class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    digest_frequency: Mapped[str] = mapped_column(String(20), default="never")
    milestone_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    review_reminders: Mapped[bool] = mapped_column(Boolean, default=True)
    verification_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    verification_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
```

- [ ] **Step 2: Create notification preferences API**

Create `src/api/notifications.py`:

```python
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import NotificationPreference, User
from src.database.session import get_session

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationPrefsRequest(BaseModel):
    email: str
    digest_frequency: str = "never"
    milestone_alerts: bool = True
    review_reminders: bool = True


class NotificationPrefsResponse(BaseModel):
    user_id: int
    email: str
    email_verified: bool
    digest_frequency: str
    milestone_alerts: bool
    review_reminders: bool


@router.get("/preferences/{user_id}", response_model=NotificationPrefsResponse)
async def get_preferences(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return prefs


@router.put("/preferences/{user_id}", response_model=NotificationPrefsResponse)
async def update_preferences(user_id: int, body: NotificationPrefsRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    prefs = result.scalar_one_or_none()
    if prefs:
        prefs.email = body.email
        prefs.digest_frequency = body.digest_frequency
        prefs.milestone_alerts = body.milestone_alerts
        prefs.review_reminders = body.review_reminders
        prefs.email_verified = False
        prefs.verification_code = None
        prefs.verification_expires = None
    else:
        from src.database.models import Base
        prefs = NotificationPreference(
            user_id=user_id,
            email=body.email,
            digest_frequency=body.digest_frequency,
            milestone_alerts=body.milestone_alerts,
            review_reminders=body.review_reminders,
        )
        session.add(prefs)
    await session.commit()
    return prefs


@router.post("/preferences/{user_id}/verify")
async def send_verification(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    code = secrets.token_hex(6)
    prefs.verification_code = code
    prefs.verification_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    await session.commit()
    return {"message": "Verification code sent", "code": code}  # TODO: send via email


@router.post("/preferences/{user_id}/verify/{code}")
async def confirm_verification(user_id: int, code: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(NotificationPreference).where(NotificationPreference.user_id == user_id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    if prefs.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid code")
    if prefs.verification_expires and prefs.verification_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Code expired")
    prefs.email_verified = True
    prefs.verification_code = None
    prefs.verification_expires = None
    await session.commit()
    return {"message": "Email verified"}
```

- [ ] **Step 3: Register router in main.py**

Read `src/main.py` and add:
```python
from src.api.notifications import router as notifications_router
app.include_router(notifications_router)
```

- [ ] **Step 4: Verify**

Run: `ruff check src/api/notifications.py` and `ruff check src/main.py`

- [ ] **Step 5: Commit**

```bash
git add src/database/models.py src/api/notifications.py src/main.py
git commit -m "feat: add notification preferences model and API"
```

---

### Task 2: Email Service

**Files:**
- Create: `src/notifications/email_service.py`
- Create: `src/notifications/templates/` (directory)

- [ ] **Step 1: Create email service module**

Create `src/notifications/__init__.py` (empty file).

Create `src/notifications/email_service.py`:

```python
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

logger = structlog.get_logger()


def get_email_config():
    return {
        "host": os.getenv("EMAIL_HOST", ""),
        "port": int(os.getenv("EMAIL_PORT", "587")),
        "user": os.getenv("EMAIL_USER", ""),
        "password": os.getenv("EMAIL_PASS", ""),
        "from": os.getenv("EMAIL_FROM", "noreply@ethiobio.com"),
        "use_tls": os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
    }


def send_email(to: str, subject: str, html_body: str) -> bool:
    config = get_email_config()
    if not config["host"]:
        logger.warning("email_not_configured", to=to, subject=subject)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = config["from"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(config["host"], config["port"]) as server:
            if config["use_tls"]:
                server.starttls()
            if config["user"]:
                server.login(config["user"], config["password"])
            server.send_message(msg)

        logger.info("email_sent", to=to, subject=subject)
        return True
    except Exception as e:
        logger.error("email_failed", to=to, subject=subject, error=str(e))
        return False
```

- [ ] **Step 2: Create Jinja2 email templates**

Create `src/notifications/templates/milestone_alert.html`:

```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #2563eb;">{{ title }}</h2>
  <p>Hi there,</p>
  <p>{{ message }}</p>
  <div style="background: #f0fdf4; border: 1px solid #22c55e; border-radius: 8px; padding: 16px; margin: 16px 0;">
    <p style="font-size: 24px; text-align: center; margin: 0;">+{{ improvement_pct }}%</p>
    <p style="text-align: center; color: #166534; margin: 4px 0 0;">Mastery improvement in <strong>{{ topic }}</strong></p>
  </div>
  <p style="color: #6b7280; font-size: 12px; margin-top: 24px;">EthioSci AI Assistant — Personalized Science Tutoring</p>
</body>
</html>
```

Create `src/notifications/templates/digest.html`:

```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #2563eb;">Your {{ frequency }} Progress Digest</h2>
  <p>Here's your biology learning summary:</p>
  {% if mastery_changes %}
  <h3>Mastery Changes</h3>
  <table style="width: 100%; border-collapse: collapse;">
    <tr style="background: #f3f4f6;">
      <th style="padding: 8px; text-align: left;">Topic</th>
      <th style="padding: 8px; text-align: right;">Change</th>
    </tr>
    {% for change in mastery_changes %}
    <tr>
      <td style="padding: 8px;">{{ change.topic }}</td>
      <td style="padding: 8px; text-align: right; color: {{ 'green' if change.improvement > 0 else 'red' }};">
        {{ '+' if change.improvement > 0 }}{{ change.improvement }}%
      </td>
    </tr>
    {% endfor %}
  </table>
  {% endif %}
  {% if due_reviews %}
  <h3>Due for Review</h3>
  <ul>
    {% for review in due_reviews %}
    <li>{{ review.topic }} — {{ review.days_overdue }}d overdue</li>
    {% endfor %}
  </ul>
  {% endif %}
  <p style="color: #6b7280; font-size: 12px; margin-top: 24px;">EthioSci AI Assistant</p>
</body>
</html>
```

Create `src/notifications/templates/review_reminder.html`:

```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; padding: 20px; max-width: 600px; margin: 0 auto;">
  <h2 style="color: #2563eb;">Review Reminder</h2>
  <p>You have topics due for review:</p>
  <ul>
    {% for topic in topics %}
    <li><strong>{{ topic.name }}</strong> — Last reviewed {{ topic.last_reviewed }}</li>
    {% endfor %}
  </ul>
  <p>Regular review helps retain what you've learned!</p>
  <p style="color: #6b7280; font-size: 12px; margin-top: 24px;">EthioSci AI Assistant</p>
</body>
</html>
```

- [ ] **Step 3: Verify**

Run: `ruff check src/notifications/`

- [ ] **Step 4: Commit**

```bash
git add src/notifications/ && git commit -m "feat: add email service and notification templates"
```

---

### Task 3: Milestone Alerts on Task Completion

**Files:**
- Modify: `src/api/recovery.py` (integrate milestone notifications)

- [ ] **Step 1: Add notification sending to task completion**

Read `src/api/recovery.py` and find the `complete_task` function. After the milestone XP check, add logic to detect significant mastery improvement and trigger milestone email notification:

```python
            # Check for mastery improvement milestone
            if prefs and prefs.milestone_alerts and prefs.email_verified:
                if mastery_improved and mastery_improved >= 10.0:
                    from src.notifications.email_service import send_email
                    from jinja2 import Environment, FileSystemLoader
                    import os
                    template_dir = os.path.join(os.path.dirname(__file__), "..", "notifications", "templates")
                    env = Environment(loader=FileSystemLoader(template_dir))
                    template = env.get_template("milestone_alert.html")
                    html = template.render(
                        title="Milestone Achieved!",
                        message=f"You improved your {topic_name} mastery by {mastery_improved:.0f}%!",
                        improvement_pct=f"{mastery_improved:.0f}",
                        topic=topic_name,
                    )
                    send_email(prefs.email, f"🎉 Milestone: +{mastery_improved:.0f}% in {topic_name}", html)
```

You need to check what variables are available — look for `mastery_improved` or similar in the existing `complete_task` function, and for `topic_name`. The `prefs` variable should be loaded from NotificationPreference earlier in the function.

- [ ] **Step 2: Verify**

Run: `ruff check src/api/recovery.py`

- [ ] **Step 3: Commit**

```bash
git add src/api/recovery.py
git commit -m "feat: send milestone email alerts on task completion"
```

---

### Task 4: Digest Sending Script

**Files:**
- Create: `scripts/send_digests.py`

- [ ] **Step 1: Create the digest script**

```python
#!/usr/bin/env python3
"""
Send daily/weekly digest emails to users who opted in.
Run via cron: 0 8 * * * cd /app && python scripts/send_digests.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from src.database.models import NotificationPreference, SpacedRepetitionSchedule, StudentMastery, User
from src.database.session import async_session_factory
from src.notifications.email_service import send_email
from jinja2 import Environment, FileSystemLoader


async def send_digests():
    factory = async_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(NotificationPreference).where(
                NotificationPreference.digest_frequency.in_(["daily", "weekly"]),
                NotificationPreference.email_verified == True,
            )
        )
        prefs_list = list(result.scalars().all())

        template_dir = os.path.join(os.path.dirname(__file__), "..", "src", "notifications", "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("digest.html")

        for prefs in prefs_list:
            try:
                # Get recent mastery changes (last 7 days)
                from src.api.recovery import _get_weak_topics
                weak_topics = await _get_weak_topics(prefs.user_id, session)

                mastery_changes = []
                if weak_topics:
                    now = datetime.now(timezone.utc)
                    for wt in weak_topics:
                        mastery_changes.append({
                            "topic": wt.topic,
                            "improvement": wt.average_score,
                        })

                # Get due reviews
                due_result = await session.execute(
                    select(SpacedRepetitionSchedule).where(
                        SpacedRepetitionSchedule.user_id == prefs.user_id,
                        SpacedRepetitionSchedule.next_review_at <= datetime.now(timezone.utc),
                    )
                )
                due = list(due_result.scalars().all())

                html = template.render(
                    frequency=prefs.digest_frequency.capitalize(),
                    mastery_changes=mastery_changes,
                    due_reviews=[{"topic": d.topic, "days_overdue": (datetime.now(timezone.utc) - d.next_review_at).days} for d in due],
                )

                subject = f"{prefs.digest_frequency.capitalize()} Biology Progress Digest"
                send_email(prefs.email, subject, html)
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.error("digest_failed", user_id=prefs.user_id, error=str(e))


if __name__ == "__main__":
    asyncio.run(send_digests())
```

- [ ] **Step 2: Make executable**

Run: `chmod +x scripts/send_digests.py`

- [ ] **Step 3: Verify**

Run: `ruff check scripts/send_digests.py`

- [ ] **Step 4: Commit**

```bash
git add scripts/send_digests.py
git commit -m "feat: add daily/weekly digest email script"
```

---

### Task 5: Question Attempt Tracking

**Files:**
- Modify: `src/database/models.py` (add QuestionAttempt model)
- Create: `src/agents/adaptive_quiz.py` (attempt recording + IRT utilities)

- [ ] **Step 1: Add QuestionAttempt model**

Add to `src/database/models.py`:

```python
class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("questions.id"))
    quiz_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("quizzes.id"), nullable=True)
    correct: Mapped[bool] = mapped_column(Boolean)
    time_spent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

- [ ] **Step 2: Create adaptive quiz module**

Create `src/agents/adaptive_quiz.py`:

```python
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import QuestionAttempt, StudentAbility, Question

logger = structlog.get_logger()


async def record_attempt(
    session: AsyncSession,
    user_id: int,
    question_id: int,
    quiz_id: int | None,
    correct: bool,
    time_spent: float | None = None,
    hints_used: int = 0,
) -> QuestionAttempt:
    # Check for previous attempts on this question
    prev_result = await session.execute(
        select(QuestionAttempt)
        .where(QuestionAttempt.user_id == user_id, QuestionAttempt.question_id == question_id)
        .order_by(QuestionAttempt.attempt_number.desc())
        .limit(1)
    )
    prev = prev_result.scalar_one_or_none()
    attempt_num = (prev.attempt_number + 1) if prev else 1

    attempt = QuestionAttempt(
        user_id=user_id,
        question_id=question_id,
        quiz_id=quiz_id,
        correct=correct,
        time_spent=time_spent,
        hints_used=hints_used,
        attempt_number=attempt_num,
    )
    session.add(attempt)
    return attempt
```

- [ ] **Step 3: Wire attempt recording into quiz submission**

Read `src/api/quiz.py` and find where quiz answers are processed. Add attempt recording after the answer is scored.

- [ ] **Step 4: Verify**

Run: `ruff check src/agents/adaptive_quiz.py`

- [ ] **Step 5: Commit**

```bash
git add src/database/models.py src/agents/adaptive_quiz.py
git commit -m "feat: add question attempt tracking model and module"
```

---

### Task 6: Student Ability Estimation (IRT)

**Files:**
- Modify: `src/database/models.py` (add StudentAbility model)
- Modify: `src/agents/adaptive_quiz.py` (add IRT ability estimation)

- [ ] **Step 1: Add StudentAbility model**

Add to `src/database/models.py`:

```python
import math

class StudentAbility(Base):
    __tablename__ = "student_abilities"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    topic: Mapped[str] = mapped_column(String(300), primary_key=True)
    ability_score: Mapped[float] = mapped_column(Float, default=0.0)
    uncertainty: Mapped[float] = mapped_column(Float, default=3.0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
```

- [ ] **Step 2: Add IRT estimation to adaptive_quiz.py**

Append to `src/agents/adaptive_quiz.py`:

```python
import math


def estimate_ability(correct_count: int, total_count: int, prior_ability: float = 0.0, prior_uncertainty: float = 3.0) -> tuple[float, float]:
    """Simple Bayesian IRT ability estimation using normal approximation."""
    if total_count == 0:
        return prior_ability, prior_uncertainty

    p = correct_count / total_count
    # Clamp to avoid log(0)
    p = max(0.01, min(0.99, p))

    # Logit: log(p / (1-p)) as ability estimate
    observed_ability = math.log(p / (1 - p))

    # Weighted average: more data = more weight on observed
    weight = min(total_count / (total_count + 5), 0.95)
    new_ability = (1 - weight) * prior_ability + weight * observed_ability
    new_uncertainty = math.sqrt(prior_uncertainty**2 / (total_count + 1))

    return new_ability, new_uncertainty


async def update_ability(
    session: AsyncSession,
    user_id: int,
    topic: str,
    correct_count: int,
    total_count: int,
) -> StudentAbility:
    result = await session.execute(
        select(StudentAbility).where(
            StudentAbility.user_id == user_id,
            StudentAbility.topic == topic,
        )
    )
    ability = result.scalar_one_or_none()

    prior = ability.ability_score if ability else 0.0
    prior_uncertainty = ability.uncertainty if ability else 3.0

    new_ability, new_uncertainty = estimate_ability(correct_count, total_count, prior, prior_uncertainty)

    if ability:
        ability.ability_score = new_ability
        ability.uncertainty = new_uncertainty
        ability.attempt_count += total_count
    else:
        ability = StudentAbility(
            user_id=user_id,
            topic=topic,
            ability_score=new_ability,
            uncertainty=new_uncertainty,
            attempt_count=total_count,
        )
        session.add(ability)

    return ability


async def get_ability(
    session: AsyncSession,
    user_id: int,
    topic: str,
) -> tuple[float, int]:
    result = await session.execute(
        select(StudentAbility).where(
            StudentAbility.user_id == user_id,
            StudentAbility.topic == topic,
        )
    )
    ability = result.scalar_one_or_none()
    if ability:
        return ability.ability_score, ability.attempt_count
    return 0.0, 0
```

- [ ] **Step 3: Wire ability update into quiz submission**

Read `src/api/quiz.py` and find where quiz submit happens. After recording attempts, call `update_ability()` with per-topic correct/total counts.

- [ ] **Step 4: Verify**

Run: `ruff check src/agents/adaptive_quiz.py`

- [ ] **Step 5: Commit**

```bash
git add src/database/models.py src/agents/adaptive_quiz.py
git commit -m "feat: add student ability model and IRT estimation"
```

---

### Task 7: Adaptive Question Selection in QuizAgent

**Files:**
- Modify: `src/agents/quiz.py` (add difficulty_score column migration handling + adaptive selection)
- Modify: `src/database/models.py` (add difficulty_score column to Question)

- [ ] **Step 1: Add difficulty_score to Question model**

Add to `Question` model in `src/database/models.py`:

```python
    difficulty_score: Mapped[float] = mapped_column(Float, default=0.0)
```

Also add a one-time migration function in `src/agents/adaptive_quiz.py`:

```python
async def migrate_difficulty_scores(session: AsyncSession):
    """Migrate existing string difficulties to numeric scores."""
    from sqlalchemy import update
    from src.database.models import Question
    result = await session.execute(select(Question).where(Question.difficulty_score == 0.0, Question.difficulty != "medium"))
    questions = list(result.scalars().all())
    for q in questions:
        mapping = {"easy": -1.0, "medium": 0.0, "hard": 1.0}
        q.difficulty_score = mapping.get(q.difficulty, 0.0)
    if questions:
        await session.commit()
```

- [ ] **Step 2: Add adaptive question selection**

Add to `src/agents/adaptive_quiz.py`:

```python
async def select_adaptive_questions(
    session: AsyncSession,
    user_id: int,
    topic: str,
    count: int = 5,
    exclude_ids: list[int] | None = None,
) -> list[Question]:
    ability, attempt_count = await get_ability(session, user_id, topic)

    # Cold start: not enough data
    if attempt_count < 5:
        query = select(Question).where(Question.topic == topic)
        if exclude_ids:
            query = query.where(Question.id.notin_(exclude_ids))
        query = query.order_by(Question.id).limit(count)
        result = await session.execute(query)
        return list(result.scalars().all())

    target = ability + 0.5  # slightly challenging
    query = select(Question).where(Question.topic == topic)
    if exclude_ids:
        query = query.where(Question.id.notin_(exclude_ids))
    result = await session.execute(query)
    available = list(result.scalars().all())

    if not available:
        return []

    # Sort by distance to target difficulty, pick closest `count`
    available.sort(key=lambda q: abs(q.difficulty_score - target))
    return available[:count]
```

- [ ] **Step 3: Integrate into QuizAgent**

Modify `src/agents/quiz.py` to accept adaptive mode. Add an optional `adaptive: bool = False` parameter to `generate()`. When adaptive, call `select_adaptive_questions()` first and pass the selected questions' difficulty distribution as a hint to the LLM prompt.

- [ ] **Step 4: Verify**

Run: `ruff check src/agents/quiz.py src/agents/adaptive_quiz.py`

- [ ] **Step 5: Commit**

```bash
git add src/database/models.py src/agents/quiz.py src/agents/adaptive_quiz.py
git commit -m "feat: add adaptive question selection with IRT-based difficulty"
```
