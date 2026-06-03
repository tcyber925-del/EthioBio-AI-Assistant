# Student Auth via Telegram OTP

## Summary

Enable students to authenticate on the dashboard using their Telegram identity via a one-time password (OTP) flow. Students who already use the Telegram bot can log into the dashboard without email/password — just their Telegram ID + a 6-digit code.

## Components

### SA-1: Student Registration (`src/api/auth.py`)

Add `"student"` to the allowed roles tuple in `POST /auth/register`. This allows students to register via email/password if desired. No other changes — the `UserRole.student` enum value already exists.

**File changes**: `src/api/auth.py` line 129 — one-line constant change.

### SA-2: Bot `/dashboard-login` Command (`src/telegram/bot.py`)

New command handler:

1. `_try_register_user(telegram_id)` — ensures user exists (already exists, reused)
2. Generate a random 6-digit numeric OTP via `random.randint(100000, 999999)`
3. Store `otp:{telegram_id}` → `{ code, created_at }` in Redis with 5-minute TTL (using existing `redis_client` from `src/redis_client`)
4. Reply with "Your dashboard login code: `123456`\n\nThis code expires in 5 minutes. Enter it on the login page at {dashboard_url}/login"

**File changes**: New handler in `src/telegram/bot.py`, register `CommandHandler("dashboard-login", dashboard_login_command)` in `build_app()`.

### SA-3: `POST /auth/request-otp` Endpoint (`src/api/auth.py`)

New endpoint allowing the dashboard to trigger OTP without requiring the user to send a bot command:

```
POST /auth/request-otp
{ telegram_id: int }
→ { success: true, message: "OTP sent to your Telegram" }
```

1. Validate that a user with this `telegram_id` exists in the DB
2. Generate 6-digit OTP
3. Store `otp:{telegram_id}` in Redis with 5-min TTL
4. Send OTP via Telegram Bot API: `POST https://api.telegram.org/bot{token}/sendMessage?chat_id={telegram_id}&text=Your dashboard login code: {code}`
5. Return success (silently if Telegram send fails — the user can always use `/dashboard-login` in the bot as fallback)

### SA-4: `POST /auth/verify-otp` Endpoint (`src/api/auth.py`)

```
POST /auth/verify-otp
{ telegram_id: int, otp: string }
→ TokenResponse { access_token, token_type, user_id, role }
```

1. Read `otp:{telegram_id}` from Redis
2. If missing → `401 OTP expired or not requested`
3. If code doesn't match → `401 Invalid OTP`
4. Look up user by `telegram_id` in DB
5. If not found → `404 User not found`
6. Issue JWT via `_create_access_token(str(user.id), user.role.value)`
7. Delete OTP from Redis (one-time use)
8. Return `TokenResponse`

### SA-5: Dashboard "Login with Telegram" Toggle (`dashboard/src/app/login/page.tsx`)

Add a toggle on the existing `/login` page:

- **Default state**: email/password form (unchanged)
- **Toggle link**: "Login with Telegram instead" / "Login with email instead"
- **Telegram OTP state**:
  - Field: "Telegram ID" (numeric input)
  - Button: "Send OTP" → calls `POST /auth/request-otp`
  - Field: "6-digit code" (disabled until OTP requested)
  - Button: "Verify & Login" → calls `POST /auth/verify-otp`
  - On success: store JWT in localStorage, redirect to `/`

## Data Flow

```
┌──────────┐    POST /auth/request-otp     ┌──────────┐
│ Dashboard │  ──────────────────────────►  │   API    │
│  /login   │  { telegram_id }              │  Server  │
│           │  ◄──────────────────────────  │          │
│           │    { success: true }          └────┬─────┘
│           │                                    │
│           │                          ┌─────────▼────────┐
│           │                          │  Redis: setex     │
│           │                          │  otp:{id} → code  │
│           │                          │  TTL: 300s        │
│           │                          └─────────┬────────┘
│           │                                    │
│           │                          ┌─────────▼────────┐
│           │                          │ Telegram Bot API │
│           │                          │ sendMessage()    │
│           │                          └──────────────────┘
│           │
│           │    POST /auth/verify-otp    ┌──────────┐
│           │  ──────────────────────────►│   API    │
│           │  { telegram_id, otp }       │  Server  │
│           │  ◄──────────────────────────│          │
│           │  { access_token, ... }      └──────────┘
```

Fallback path (user can also type `/dashboard-login` in the bot):

```
User ──► Telegram Bot ──► Redis ──► Dashboard verify
```

## Redis Schema

| Key | Value | TTL |
|-----|-------|-----|
| `otp:{telegram_id}` | `{ code: "123456", created_at: "2026-06-03T..." }` | 300s |

## Error Scenarios

| Scenario | HTTP | Response |
|----------|------|----------|
| No OTP requested | 401 | `OTP not requested or expired` |
| Wrong OTP | 401 | `Invalid OTP` |
| OTP expired | 401 | `OTP not requested or expired` |
| Unknown telegram_id | 404 | `User not found for this Telegram ID` |
| Reuse OTP | 401 | `OTP not requested or expired` (already deleted) |

## Files Changed

| File | Change |
|------|--------|
| `src/redis_client.py` | New module exporting `get_redis() → redis.asyncio.Redis` (lazy singleton) |
| `src/api/auth.py` | Add `"student"` to allowed roles; add `POST /auth/request-otp`; add `POST /auth/verify-otp` |
| `src/telegram/bot.py` | Add `dashboard_login_command` handler; register `CommandHandler` |
| `src/config.py` | (no change needed — `telegram_bot_token` and `redis_url` already exist) |
| `dashboard/src/app/login/page.tsx` | Add "Login with Telegram" toggle with OTP form |
| `dashboard/src/lib/auth.ts` | (no change — existing JWT storage works unchanged) |

## Testing

- `tests/test_auth.py`: Test OTP generation, Redis storage, verification, expiry, invalid OTP, reuse prevention
- Bot command: Manual test via Telegram (can't unit test without bot token)
- Dashboard: Visual check — toggle renders, form switches, OTP flow works end-to-end
