# Telegram Bot Parent Notifications — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Telegram bot commands for parents to link accounts, view children's progress, and receive proactive daily reminders.

**Architecture:** Three new command/callback handlers in `src/telegram/bot.py` querying the DB directly via `async_session_factory`; proactive reminders extend `scripts/send_proactive_reminders.py`.

**Tech Stack:** Python 3.12+, python-telegram-bot v21+, SQLAlchemy async, PostgreSQL

---

### Task 1: TB-P1 — `/parent_register` command handler

**Files:**
- Modify: `src/telegram/bot.py`

**Details:** New `register_parent` command handler that links a Telegram user to an existing parent account via email.

- [ ] **Step 1: Add `register_parent` handler to `bot.py`**

Add near the other command handlers (after `dashboard_login_command`, around line 96):

```python
async def register_parent(update: Update, context):
    email = (context.args[0] if context.args else "").strip().lower()
    if not email:
        await update.message.reply_text(
            "Usage: <code>/parent_register your@email.com</code>\n\n"
            "You need a parent account on the dashboard first. "
            "Register at the dashboard, then link your Telegram here.",
            parse_mode="HTML",
        )
        return

    async def _link():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(User).where(
                    User.email == email,
                    User.role == UserRole.parent,
                    User.is_active == True,
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                await update.message.reply_text(
                    "No parent account found with that email. "
                    "Make sure you registered as a parent on the dashboard first."
                )
                return
            if user.telegram_id and user.telegram_id != update.effective_user.id:
                await update.message.reply_text(
                    "This account is already linked to another Telegram user. "
                    "Contact support if you need to relink."
                )
                return
            user.telegram_id = update.effective_user.id
            await session.commit()
            await update.message.reply_text(
                "✅ Telegram linked! Use /children to view your children's progress."
            )
    await _db_try(_link)
```

- [ ] **Step 2: Register the handler in `build_app()`**

After the existing `CommandHandler("dashboard-login", dashboard_login_command)` registration, add:
```python
    app.add_handler(CommandHandler("parent_register", register_parent))
```

- [ ] **Step 3: Verify it parses**

Run: `python -c "import ast; ast.parse(open('src/telegram/bot.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat: add /parent_register bot command"
```

---

### Task 2: TB-P2 + TB-P3 — `/children` command + child progress callbacks

**Files:**
- Modify: `src/telegram/bot.py`
- Test: `tests/test_telegram_bot.py`

- [ ] **Step 1: Add `list_children` handler**

Add after `register_parent`:
```python
async def list_children(update: Update, context):
    telegram_id = update.effective_user.id

    async def _fetch():
        factory = async_session_factory()
        async with factory() as session:
            user_result = await session.execute(
                select(User).where(
                    User.telegram_id == telegram_id,
                    User.is_active == True,
                )
            )
            user = user_result.scalar_one_or_none()
            if not user or user.role != UserRole.parent:
                await update.message.reply_text(
                    "Please register first with /parent_register"
                )
                return

            children_result = await session.execute(
                select(User)
                .join(ParentChild, User.id == ParentChild.student_id)
                .where(ParentChild.parent_id == user.id)
            )
            children = list(children_result.scalars().all())

            if not children:
                await update.message.reply_text(
                    "No children linked to your account yet. "
                    "Ask an admin to link your children, or check the dashboard."
                )
                return

            keyboard = []
            lines = ["<b>Your Children:</b>\n"]
            for child in children:
                profile_result = await session.execute(
                    select(StudentProfile).where(StudentProfile.user_id == child.id)
                )
                profile = profile_result.scalar_one_or_none()
                grade = child.grade_level or profile.grade_level if profile else None
                lines.append(
                    f"👤 {child.email or 'Student'} "
                    f"{f'(Grade {grade})' if grade else ''}"
                )
                keyboard.append([
                    InlineKeyboardButton(
                        f"🔍 {child.email or 'View Progress'}",
                        callback_data=f"parent_child_{child.id}",
                    )
                ])
            keyboard.append([InlineKeyboardButton("← Back to Menu", callback_data="menu")])

            await update.message.reply_text(
                "\n".join(lines),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    await _db_try(_fetch)
```

- [ ] **Step 2: Add `handle_parent_child_progress` callback handler**

Add after `list_children`:
```python
async def handle_parent_child_progress(update: Update, context):
    query = update.callback_query
    await query.answer()
    child_id = query.data.replace("parent_child_", "")

    async def _fetch():
        factory = async_session_factory()
        async with factory() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            parent = user_result.scalar_one_or_none()
            if not parent:
                await query.edit_message_text("Parent account not found.")
                return

            ownership = await session.execute(
                select(ParentChild).where(
                    ParentChild.parent_id == parent.id,
                    ParentChild.student_id == child_id,
                )
            )
            if not ownership.scalar_one_or_none():
                await query.edit_message_text("Child not found.")
                return

            child_result = await session.execute(select(User).where(User.id == child_id))
            child = child_result.scalar_one_or_none()
            if not child:
                await query.edit_message_text("Student not found.")
                return

            mastery_result = await session.execute(
                select(StudentMastery).where(StudentMastery.user_id == child.id)
            )
            mastery_records = list(mastery_result.scalars().all())

            quiz_result = await session.execute(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == child.id)
                .order_by(QuizAttempt.created_at.desc())
                .limit(5)
            )
            recent_quizzes = list(quiz_result.scalars().all())

            gam_result = await session.execute(
                select(UserGamification).where(UserGamification.user_id == child.id)
            )
            gam = gam_result.scalar_one_or_none()

            score = sum(
                r.correct / max(r.total, 1) * 100 for r in recent_quizzes
            ) / max(len(recent_quizzes), 1) if recent_quizzes else 0

            lines = [f"<b>📚 {child.email or 'Student'}'s Progress</b>\n"]
            lines.append(f"🎯 Readiness: {score:.0f}%")
            lines.append(f"🔥 Streak: {gam.streak if gam else 0} days")
            lines.append(f"💎 XP: {gam.total_xp if gam else 0}\n")

            if mastery_records:
                lines.append("<b>Topic Mastery:</b>")
                for m in mastery_records[:5]:
                    lines.append(f"• {m.topic}: {m.mastery_score:.0f}%")
                lines.append("")

            if recent_quizzes:
                lines.append("<b>Recent Quizzes:</b>")
                for q in recent_quizzes:
                    pct = q.correct / max(q.total, 1) * 100
                    lines.append(f"• {q.id} — {pct:.0f}%")

            keyboard = [
                [InlineKeyboardButton("📋 Weekly Summary", callback_data=f"parent_summary_{child.id}")],
                [InlineKeyboardButton("← Back to Children", callback_data="children")],
            ]
            await query.edit_message_text(
                "\n".join(lines),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    await _db_try(_fetch)
```

- [ ] **Step 3: Add `handle_parent_summary` callback handler**

Add after `handle_parent_child_progress`:
```python
async def handle_parent_summary(update: Update, context):
    query = update.callback_query
    await query.answer()
    child_id = query.data.replace("parent_summary_", "")

    async def _fetch():
        factory = async_session_factory()
        async with factory() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            parent = user_result.scalar_one_or_none()
            if not parent:
                await query.edit_message_text("Parent account not found.")
                return

            ownership = await session.execute(
                select(ParentChild).where(
                    ParentChild.parent_id == parent.id,
                    ParentChild.student_id == child_id,
                )
            )
            if not ownership.scalar_one_or_none():
                await query.edit_message_text("Child not found.")
                return

            child_result = await session.execute(select(User).where(User.id == child_id))
            child = child_result.scalar_one_or_none()
            if not child:
                await query.edit_message_text("Student not found.")
                return

            profile_result = await session.execute(
                select(StudentProfile).where(StudentProfile.user_id == child.id)
            )
            profile = profile_result.scalar_one_or_none()

            from datetime import datetime, timedelta, timezone
            week_end = datetime.now(timezone.utc)
            week_start = week_end - timedelta(days=7)

            records_result = await session.execute(
                select(ProgressRecord)
                .where(
                    ProgressRecord.student_id == child.id,
                    ProgressRecord.created_at >= week_start,
                    ProgressRecord.created_at <= week_end,
                )
            )
            records = list(records_result.scalars().all())

            from src.agents.parent_summary import ParentSummaryAgent
            from src.llm.router import ModelRouter
            agent = ParentSummaryAgent(ModelRouter())
            summary = await agent.generate_summary(
                student_name=child.email or "Student",
                grade_level=child.grade_level,
                records=records,
                profile=profile,
                week_start=week_start,
                week_end=week_end,
                language="en",
                session=session,
            )

            text = f"<b>Weekly Summary</b>\n\n{summary['summary_text']}"
            if summary.get("summary_amharic"):
                text += f"\n\n———\n{summary['summary_amharic']}"

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("← Back to Progress", callback_data=f"parent_child_{child_id}")],
                ]),
            )
    await _db_try(_fetch)
```

- [ ] **Step 4: Add `children_list` callback handler** (for "← Back to Children" button)

Add a simple handler that re-displays the children list when the user presses "← Back to Children":
```python
async def handle_children_back(update: Update, context):
    query = update.callback_query
    await query.answer()
    await list_children(update, context)
```

- [ ] **Step 5: Register all new handlers in `build_app()`**

After the existing `CommandHandler` registrations, add:
```python
    app.add_handler(CommandHandler("children", list_children))
```

After the existing `CallbackQueryHandler` registrations, add:
```python
    app.add_handler(CallbackQueryHandler(handle_parent_child_progress, pattern=r"^parent_child_"))
    app.add_handler(CallbackQueryHandler(handle_parent_summary, pattern=r"^parent_summary_"))
    app.add_handler(CallbackQueryHandler(handle_children_back, pattern="^children$"))
```

- [ ] **Step 6: Verify it parses**

Run: `python -c "import ast; ast.parse(open('src/telegram/bot.py').read()); print('OK')`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat: add /children command and child progress callbacks"
```

---

### Task 3: TB-P4 — Proactive parent reminders

**Files:**
- Modify: `scripts/send_proactive_reminders.py`

- [ ] **Step 1: Add parent notification section to `send_proactive_reminders.py`**

Read the file first to understand the existing structure. Then add the following block after the student reminder section (before the closing `if __name__ == "__main__":` block):

```python
    # ── Parent notifications ──
    parent_result = await db.execute(
        select(User).where(
            User.role == UserRole.parent,
            User.telegram_id.isnot(None),
            User.is_active == True,
        )
    )
    parents = list(parent_result.scalars().all())

    for parent in parents:
        try:
            children_result = await db.execute(
                select(User)
                .join(ParentChild, User.id == ParentChild.student_id)
                .where(ParentChild.parent_id == parent.id)
            )
            children = list(children_result.scalars().all())
            if not children:
                continue

            lines = [f"👋 <b>Daily Update</b>\n"]
            has_activity = False
            for child in children:
                profile_result = await db.execute(
                    select(StudentProfile).where(StudentProfile.user_id == child.id)
                )
                profile = profile_result.scalar_one_or_none()

                quiz_result = await db.execute(
                    select(QuizAttempt)
                    .where(
                        QuizAttempt.user_id == child.id,
                        QuizAttempt.created_at >= now - timedelta(hours=24),
                    )
                    .order_by(QuizAttempt.created_at.desc())
                    .limit(3)
                )
                recent = list(quiz_result.scalars().all())

                name = child.email or f"Student {str(child.id)[:8]}"
                grade = child.grade_level or (profile.grade_level if profile else None)
                lines.append(f"👤 <b>{name}</b>{f' (Grade {grade})' if grade else ''}")

                if recent:
                    has_activity = True
                    for q in recent:
                        pct = q.correct / max(q.total, 1) * 100
                        lines.append(f"  • Quiz: {pct:.0f}% correct")
                else:
                    lines.append(f"  No new activity in the last 24h")

                lines.append("")

            if not has_activity:
                continue

            lines.append(f"📋 <a href='{settings.dashboard_url}/parent'>View full dashboard</a>")

            await bot.send_message(
                chat_id=parent.telegram_id,
                text="\n".join(lines),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            sent_count += 1
        except Exception as e:
            logger.warning("parent_notification_error", parent_id=str(parent.id), error=str(e))
```

- [ ] **Step 2: Verify imports in `send_proactive_reminders.py`**

Check that the file already imports the needed models. It needs `UserRole`, `ParentChild`, `StudentProfile`, `QuizAttempt`. If any are missing, add to the existing imports block.

- [ ] **Step 3: Lint the script**

Run: `.venv/bin/ruff check scripts/send_proactive_reminders.py`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add scripts/send_proactive_reminders.py
git commit -m "feat: add parent daily reminders to proactive notification script"
```

---

### Task 4: Full quality check

- [ ] **Step 1: Backend lint**

Run: `.venv/bin/ruff check src/telegram/bot.py scripts/send_proactive_reminders.py`
Expected: No new errors (only pre-existing E501)

- [ ] **Step 2: Verify parse**

Run: `python -c "import ast; ast.parse(open('src/telegram/bot.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Push**

```bash
git push origin ralph/readiness-cl-integration
```
