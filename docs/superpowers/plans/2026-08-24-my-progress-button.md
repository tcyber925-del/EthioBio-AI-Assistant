# My Progress Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the main-menu "📊 My Progress" button (and `/progress`) to a real student overview: readiness %, streak, XP/level, topic mastery bars, focus suggestion.

**Architecture:** One shared DB fetcher (`fetch_progress_overview`) + one pure formatter (`_format_progress_overview`) in `bot.py`, called by both the callback handler and the `/progress` command, wrapped in the existing `_db_try` pattern. Onboarding empty-state for zero-data users.

**Tech Stack:** Python 3.12, PTB v20+, SQLAlchemy async, pytest + AsyncMock, i18n via `src/telegram/i18n.t()`.

**Files:**
- Modify: `src/telegram/bot.py` (imports ~line 1, handlers at :2061, :2701)
- Modify: `src/telegram/messages/en.json`, `src/telegram/messages/am.json` (`progress` section, line ~111)
- Test: `tests/test_telegram_bot.py`

---

## Task 1: i18n keys

- [ ] **Step 1:** Replace the `"progress"` object in `en.json` (line 111) with:

```json
"progress": {
    "title": "📊 My Progress",
    "readiness": "Readiness",
    "streak": "Streak",
    "best": "best",
    "level": "Level",
    "topic_mastery": "📚 Topic Mastery",
    "focus_next": "Focus next",
    "empty": "📊 No progress yet!\n\nTake your first quiz and your scores, streak, and topic mastery will show up here.",
    "need_start": "Please /start first to register."
},
```

(`no_weak` is removed — the new overview shows all topics, so the special case disappears.)

- [ ] **Step 2:** Replace the `"progress"` object in `am.json` (line 111) with:

```json
"progress": {
    "title": "📊 እድገቴ",
    "readiness": "ዝግጁነት",
    "streak": "ተከታታይ",
    "best": "ከፍተኛ",
    "level": "ደረጃ",
    "topic_mastery": "📚 የርዕሶች ዕውቀት",
    "focus_next": "ቀጥሎ ማተኮር ያለበት",
    "empty": "📊 እስካሁን እድገት የለም!\n\nየመጀመሪያውን ፈተና ይውሰዱ — ውጤቶችዎ፣ ተከታታይ ቀናትዎ እና የርዕስ ዕውቀትዎ እዚህ ይታያሉ።",
    "need_start": "እባክዎ መጀመሪያ /start ይጠቀሙ።"
},
```

- [ ] **Step 3:** Verify keys resolve:

Run: `python -c "from src.telegram.i18n import t; assert 'My Progress' in t('progress.title','en'); assert 'እድገቴ' in t('progress.title','am'); print('ok')"`
Expected: `ok`

- [ ] **Step 4:** Commit: `git commit -m "feat(bot): add progress overview i18n keys"`

## Task 2: Pure formatter (TDD)

- [ ] **Step 1:** Add failing tests to `tests/test_telegram_bot.py`:

```python
def test_format_progress_overview_renders_stats_and_bars():
    gam = SimpleNamespace(total_xp=1250, level=3, current_streak=4, longest_streak=9)
    quizzes = [SimpleNamespace(correct=7, total=10), SimpleNamespace(correct=8, total=10)]
    masteries = [
        SimpleNamespace(topic="Cell Biology", mastery_score=82.0),
        SimpleNamespace(topic="Evolution", mastery_score=30.0),
    ]
    text = bot._format_progress_overview(
        {"gam": gam, "recent_quizzes": quizzes, "mastery_records": masteries}
    )
    assert "75%" in text
    assert "Cell Biology" in text and "82%" in text
    assert "Focus next" in text and "Evolution" in text
    assert "<b>" in text


def test_format_progress_overview_escapes_topics_and_defaults_gamification():
    masteries = [SimpleNamespace(topic="Cells <&> DNA", mastery_score=50.0)]
    text = bot._format_progress_overview(
        {"gam": None, "recent_quizzes": [], "mastery_records": masteries}
    )
    assert "Cells &lt;&amp;&gt; DNA" in text
    assert "Level 1" in text and "0 XP" in text
```

- [ ] **Step 2:** Run `pytest tests/test_telegram_bot.py -k format_progress -v` → expect FAIL (`AttributeError`).
- [ ] **Step 3:** Implement in `bot.py` above `handle_progress`. Add `import html` to stdlib imports (top of file). Then:

```python
def _format_progress_overview(data: dict, language: str = "en") -> str:
    gam = data["gam"]
    quizzes = data["recent_quizzes"]
    masteries = data["mastery_records"]

    readiness = (
        sum(q.correct / max(q.total, 1) * 100 for q in quizzes) / len(quizzes) if quizzes else 0.0
    )

    lines = [f"<b>{t('progress.title', language)}</b>", ""]
    lines.append(f"🎯 {t('progress.readiness', language)}: <b>{readiness:.0f}%</b>")
    best = gam.longest_streak if gam else 0
    lines.append(
        f"🔥 {t('progress.streak', language)}: {gam.current_streak if gam else 0}"
        f" ({t('progress.best', language)}: {best})"
    )
    lines.append(
        f"💎 {t('progress.level', language)} {gam.level if gam else 1} · {gam.total_xp if gam else 0} XP"
    )

    if masteries:
        lines += ["", f"<b>{t('progress.topic_mastery', language)}</b>"]
        for m in masteries[:5]:
            score = max(0, min(round(m.mastery_score), 100))
            bar = "█" * round(score / 10) + "░" * (10 - round(score / 10))
            icon = "🔴" if score < 40 else "🟡" if score < 60 else "🟢" if score < 80 else "💚"
            lines.append(f"{icon} {html.escape(str(m.topic))} {bar} {score}%")

    weakest = min(masteries, key=lambda m: m.mastery_score) if masteries else None
    if weakest:
        lines += ["", f"👉 {t('progress.focus_next', language)}: <b>{html.escape(str(weakest.topic))}</b>"]
    return "\n".join(lines)
```

- [ ] **Step 4:** Re-run Step 2 → PASS. Commit: `feat(bot): progress overview formatter`.

## Task 3: Fetcher + button handler (TDD)

- [ ] **Step 1:** Add failing handler tests (reuse the file's `mock_factory` pattern):

```python
def _db_result(scalar=None, scalars=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar
    inner = MagicMock()
    inner.all.return_value = scalars or []
    r.scalars.return_value = inner
    return r


def _progress_session_mock(side_effects):
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(side_effect=side_effects)
    return mock_session


@pytest.mark.asyncio
async def test_handle_progress_shows_onboarding_for_zero_data_user(monkeypatch):
    user = SimpleNamespace(id="u1")
    monkeypatch.setattr(
        bot, "async_session_factory",
        MagicMock(return_value=_progress_session_mock([
            _db_result(scalar=user), _db_result(scalar=None),
            _db_result(scalars=[]), _db_result(scalars=[]),
        ])),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock(), message=message)
    update = SimpleNamespace(callback_query=query)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    kwargs = query.edit_message_text.await_args.kwargs
    assert "first quiz" in query.edit_message_text.await_args.args[0]
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_handle_progress_shows_overview_for_returning_user(monkeypatch):
    user = SimpleNamespace(id="u1")
    gam = SimpleNamespace(total_xp=500, level=2, current_streak=2, longest_streak=5)
    monkeypatch.setattr(
        bot, "async_session_factory",
        MagicMock(return_value=_progress_session_mock([
            _db_result(scalar=user), _db_result(scalar=gam),
            _db_result(scalars=[SimpleNamespace(correct=6, total=10)]),
            _db_result(scalars=[SimpleNamespace(topic="Genetics", mastery_score=55.0)]),
        ])),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock(), message=message)
    update = SimpleNamespace(callback_query=query)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    assert "Readiness" in query.edit_message_text.await_args.args[0]


@pytest.mark.asyncio
async def test_handle_progress_need_start_when_unregistered(monkeypatch):
    monkeypatch.setattr(
        bot, "async_session_factory",
        MagicMock(return_value=_progress_session_mock([_db_result(scalar=None)])),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock(), message=message)
    update = SimpleNamespace(callback_query=query)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    assert "/start" in query.edit_message_text.await_args.args[0]
```

- [ ] **Step 2:** Run → FAIL (stub text still returned).
- [ ] **Step 3:** Replace `handle_progress` body (bot.py:2061-2090) with:

```python
async def handle_progress(update: Update, context):
    query = update.callback_query
    if query:
        await query.answer()
    language = _lang(context)
    telegram_id = update.effective_user.id

    async def _show():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            keyboard = main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=language
            )
            if not user:
                text = t("progress.need_start", language)
            else:
                data = await fetch_progress_overview(user.id, session)
                if not data["recent_quizzes"] and not data["mastery_records"]:
                    text = t("progress.empty", language)
                    keyboard = InlineKeyboardMarkup(
                        [[InlineKeyboardButton(t("take_quiz", language), callback_data="quiz")]]
                    )
                else:
                    text = _format_progress_overview(data, language)

            if query:
                try:
                    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
                except Exception:
                    logger.warning("progress_edit_failed", user_id=telegram_id, exc_info=True)
                    await query.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

    await _db_try(_show)


async def fetch_progress_overview(user_id, session) -> dict:
    """Fetch gamification, recent quizzes, and mastery rows for the progress overview."""
    gam = (
        await session.execute(
            select(UserGamification).where(UserGamification.user_id == user_id)
        )
    ).scalar_one_or_none()
    quizzes = list(
        (
            await session.execute(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id)
                .order_by(QuizAttempt.created_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    masteries = list(
        (
            await session.execute(
                select(StudentMastery)
                .where(StudentMastery.user_id == user_id)
                .order_by(StudentMastery.mastery_score.desc())
            )
        )
        .scalars()
        .all()
    )
    return {"gam": gam, "recent_quizzes": quizzes, "mastery_records": masteries}
```

- [ ] **Step 4:** **Delete the old stub-pinning test** `test_handle_progress_replies_new_message_for_callback` (tests/test_telegram_bot.py:202-215) — superseded by the three new tests. Run `pytest tests/test_telegram_bot.py -k progress -v` → PASS. Commit: `feat(bot): wire My Progress button to real student overview`.

## Task 4: Unify `/progress` command (TDD)

- [ ] **Step 1:** Failing test:

```python
@pytest.mark.asyncio
async def test_progress_command_sends_overview(monkeypatch):
    user = SimpleNamespace(id="u1")
    gam = SimpleNamespace(total_xp=100, level=1, current_streak=1, longest_streak=1)
    monkeypatch.setattr(bot, "_reply_long", AsyncMock())
    monkeypatch.setattr(
        bot, "async_session_factory",
        MagicMock(return_value=_progress_session_mock([
            _db_result(scalar=user), _db_result(scalar=gam),
            _db_result(scalars=[SimpleNamespace(correct=5, total=10)]),
            _db_result(scalars=[SimpleNamespace(topic="Genetics", mastery_score=55.0)]),
        ])),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.progress_command(update, context)

    args, kwargs = bot._reply_long.await_args
    assert "Readiness" in args[1] and kwargs.get("parse_mode") == "HTML"
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Replace `progress_command` body (bot.py:2701-2746) with:

```python
async def progress_command(update: Update, context):
    telegram_id = update.effective_user.id
    language = _lang(context)

    async def _handle():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                await _reply_long(update, t("progress.need_start", language))
                return
            data = await fetch_progress_overview(user.id, session)
            if not data["recent_quizzes"] and not data["mastery_records"]:
                await _reply_long(update, t("progress.empty", language), parse_mode="HTML")
                return
            await _reply_long(
                update, _format_progress_overview(data, language), parse_mode="HTML"
            )

    await _db_try(_handle)
```

- [ ] **Step 4:** Run → PASS. Commit: `refactor(bot): unify /progress with button overview`.

## Task 5: Verification gate

- [ ] `ruff check . && mypy src/` — clean
- [ ] `pytest tests/ -v -k "not slow"` — green (coverage floor 50% unaffected)
- [ ] `pre-commit run --all-files`
- [ ] Manual smoke (needs Postgres + bot token): `/start` → tap 📊 My Progress → overview renders; fresh account → onboarding + Take a Quiz button; `/progress` matches button output; switch language to Amharic → Amharic labels.

**Notes for executor:** All models/imports (`User`, `QuizAttempt`, `StudentMastery`, `UserGamification`, `select`, `async_session_factory`, `main_menu_keyboard`) already imported in bot.py. Only `import html` must be added. Do NOT touch parent views (`_send_child_progress`) or recovery views.

---

## Implementation Deviations (final, as shipped)

Discovered during execution — plan snippets referenced non-existent model columns:

- `QuizAttempt` has no `created_at`/`correct`; ordering uses `started_at.desc()`, readiness uses stored `score` (0-100 pct, nullable → `or 0.0`).
- `StudentMastery` has no `mastery_score`; display/focus use `average_score`.
- `/progress` sends via `update.message.reply_text`, NOT `_reply_long` (its markdown pipeline escapes pre-built HTML).
- Both paths return `has_data` from the fetcher; empty-state on BOTH paths offers the Take-a-Quiz button; overview/need_start paths attach the main menu keyboard.
- Bar fill uses `int(score // 10)` (floor), tests canonicalized to real column shapes.
