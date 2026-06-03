# Telegram Bot Parent Notifications

## Summary

Add three Telegram bot commands (`/parent_register`, `/children`, `/child_progress`) for parents to link their Telegram account, view their children's progress, and get proactive daily reminders via the existing cron script.

## Architecture

All data queried directly from the database using the bot's existing `async_session_factory` pattern — no API calls. Proactive reminders extend the existing `scripts/send_proactive_reminders.py` cron script.

## Components

### TB-P1: `/parent_register` command (`src/telegram/bot.py`)

New command handler:

1. Extracts email from command args: `/parent_register email@example.com`
2. If no args → replies "Usage: `/parent_register your@email.com`"
3. Queries `User` where `email == email AND role == parent AND is_active == True`
4. If not found → "No parent account found with that email. Register on the dashboard first."
5. If found:
   - Check if user already has `telegram_id` set (if so, confirm overwrite)
   - Set `user.telegram_id = update.effective_user.id`
   - Commit via `_db_try(_save)`
   - Reply: "✅ Telegram linked! Use /children to view your children's progress."
6. Register as `CommandHandler("parent_register", register_parent)` in `build_app()`

**Security**: Direct email match. A parent must already have a dashboard account with `role=parent`. The email is the key — if someone knows the email, they can link. This matches the trust model of Telegram bot auth (the email was set by the user during registration).

### TB-P2: `/children` command (`src/telegram/bot.py`)

New command handler:

1. Query user by `telegram_id`
2. If not found or role != parent → "Please register first with /parent_register"
3. Query `ParentChild` for `parent_id == user.id`, eager-load children
4. For each child, get `StudentProfile` and compute readiness
5. Format response:
   ```
   Your Children:
   
   👤 {name} (Grade {grade})
   📊 Readiness: {score}%
   ⭐ Streak: {streak} days
   ```
6. Each child gets an inline button `🔍 View Progress` → callback `parent_child_{id}`
7. Register as `CommandHandler("children", list_children)` + `CallbackQueryHandler(handle_parent_child_progress, pattern="^parent_child_")`

### TB-P3: Child progress detail (`src/telegram/bot.py`)

New callback handler for `^parent_child_`:

1. Extract child ID from callback data
2. Verify ownership: confirm `ParentChild` row exists for this parent+child
3. Query: StudentMastery records, recent 5 QuizAttempts, UserGamification (streak, XP)
4. Format response:
   ```
   📚 {name}'s Progress
   
   🎯 Overall Readiness: {score}%
   🔥 Streak: {streak} days
   💎 Total XP: {xp}
   
   📖 Recent Activity:
   • {title} — {score}% ({date})
   
   Weak Areas:
   • {topic} ({score}%) — needs practice
   ```
5. Add inline buttons: `📋 Weekly Summary` → callback `parent_summary_{id}`, `← Back` → callback `children`

Second callback handler for `^parent_summary_`:

1. Extract child ID
2. Call `ParentSummaryAgent.generate_summary()` (same as the API endpoint)
3. Send the summary text (may need `_reply_long` for splitting)

### TB-P4: Proactive parent reminders (`scripts/send_proactive_reminders.py`)

Extend the existing cron script:

1. After iterating students for due reviews/recovery plans, add a parent loop
2. Query all `User` where `role == parent AND telegram_id IS NOT NULL AND is_active == True`
3. For each parent, query their linked children via `ParentChild`
4. For each child, check recent activity (QuizAttempts in last 24h, mastery changes)
5. If any child has new activity, send a message:
   ```
   👋 Daily Update for {child_name}
   
   • Recent quiz: {topic} — {score}%
   • 📋 Full dashboard: {dashboard_url}/parent
   ```
6. No LLM call needed — just format existing DB data

## Data Flow

```
TB-P1: User → /parent_register email → bot → DB (update User.telegram_id) → reply

TB-P2: User → /children → bot → DB (query ParentChild) → reply + inline buttons

TB-P3: User → tap button → callback_query → bot → DB (query progress) → reply

TB-P4: cron → send_proactive_reminders.py → DB (query parents + children) → Telegram Bot API
```

## Files Changed

| File | Change |
|------|--------|
| `src/telegram/bot.py` | Add `register_parent`, `list_children`, `handle_parent_child_progress`, `handle_parent_summary` handlers; register in `build_app()` |
| `src/telegram/keyboards.py` | Add helper for parent child list keyboard (optional — can inline in bot.py) |
| `scripts/send_proactive_reminders.py` | Add parent notification section after student reminders |

## Testing

- Unit tests for DB queries: `tests/test_telegram_bot.py` (existing pattern)
- Manual testing via Telegram for `/parent_register`, `/children`, callback flow
- Proactive reminders testable by running the script manually
