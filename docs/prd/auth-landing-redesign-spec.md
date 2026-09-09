# Spec: Role-First Auth & Landing Redesign

- **Status:** Approved for implementation
- **Date:** 2026-09-04
- **Scope:** `dashboard/` (Next.js 14, Clerk), `src/api/auth.py`, `src/database/models.py`, landing page
- **Related:** `docs/adr/0013-role-first-signup-wizard.md`, `dashboard/docs/adr/0001-cutover.md`

---

## 1. Summary

Replace the single 300-line `/login` mega-component (sign-in + register + email-verify +
role-claim in one `useState` machine) with a **role-first, URL-driven signup wizard**
modeled on Khan Academy's flow, and polish the landing page (teacher banner, role-aware
CTAs, FAQ, stale-copy cleanup). Backend gains the missing identity fields (DOB, ToS
acceptance, onboarding state) and the endpoints to write them.

**Design north star:** Khan Academy's signup UX — role chosen first, one thing per page,
"Choose a different role" escape hatch — rendered in **our** design system.

## 2. Resolved decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Auth page theme | **Light v2 "Calm Educational Intelligence"** | Task UI, not brand theater; matches where users land post-auth. Marketing landing stays dark Verge. |
| D2 | Age handling | **Collect DOB for learners; under-13 requires parent email** | Product serves Grades 7–12 (ages ~12–18); enables age-appropriate UX and a consent hook. |
| D3 | OAuth providers | **Google + Microsoft** | Microsoft matters for schools/teachers; Clerk config-only. No Apple/Facebook (low ET relevance). |
| D4 | Telegram CTA | **Keep** ("Try on Telegram" hero CTA, footer link, console mock) | Live service (`t.me/ethiobio_bot`); primary low-bandwidth acquisition channel in Ethiopia. Repositioned as secondary, not removed. |
| D5 | Telegram OTP | **Remove stale references** (footer "Login / Verify OTP") | OTP auth retired in Clerk migration (`dfe1bb1`); stale copy is a bug. |

## 3. Goals / non-goals

**Goals**
- Role-first signup: Learner / Teacher / Parent selection is the entry point.
- URL-driven wizard: every step is a route (back-button safe, deep-linkable, resumable).
- One canonical post-auth destination resolver (replaces 4 scattered redirect sites).
- DOB + ToS + onboarding state persisted server-side.
- Landing polish: teacher banner, role-aware CTAs, FAQ (en/am, JSON-LD), footer fixes.
- Fonts actually load (Inter, Spectral, JetBrains Mono, Noto Sans Ethiopic).

**Non-goals (file as separate tickets)**
- Workspace API auth hardening (`src/api/workspace.py` has no `get_current_user` — **urgent security ticket**).
- Telegram ↔ web account linking (bot users have no `clerk_id`).
- Teacher identity verification queue (teachers currently self-declare with no checks).
- README/auth docs refresh for the retired OTP/cookie-JWT era.
- Donation/sustainability surface (Khan-style "$1 = …" — deferred, no payment infra).

## 4. Current state (as-built, for reference)

```
/  (marketing, dark Verge)
  │ "Launch App" → /login
  ▼
/login  = /sign-in = /sign-up   (one component, useState: form → verifyStep → claimStep)
  ├─ email/password ── Clerk signIn.create / signUp.create + email_code
  ├─ Google OAuth ──── /sso-callback ── role_claimed=false? → /login?role_claim=1
  └─ role picker → POST /auth/claim-role   (AFTER account creation)
  ▼
/v2/overview → switch(role) → role dashboard
```

Key files: `dashboard/src/app/(marketing)/login/page.tsx`, `.../sso-callback/page.tsx`,
`dashboard/src/middleware.ts`, `dashboard/src/lib/auth.ts`, `src/api/auth.py`
(`/auth/me`, `/auth/claim-role`, `/auth/public-stats`), `src/auth/clerk.py` (JWKS).

Known gaps this spec fixes: inverted role flow, no DOB/consent, no forgot-password,
`grade_level` write-only-by-nobody, fonts never loaded, no FAQ, stale OTP copy,
4 scattered post-auth redirect sites.

## 5. Target UX flows

### 5.1 Signup (new)

```
/sign-up                     Role selection: "Join EthioSci as…" (Learner / Teacher / Parent)
  │                          Reads ?role= to pre-select (entry from landing role panels/banner)
  ├─ learner → /sign-up/learner        DOB (Month/Day/Year selects) → age gate
  │            ├─ age ≥ 13 → /sign-up/account?role=learner
  │            └─ age < 13 → /sign-up/learner/consent   (parent email → consent notice;
  │                                                     account created inactive until consent)
  ├─ teacher/parent → /sign-up/account?role=…
  │
  ▼
/sign-up/account             ToS/Privacy checkbox (required) · Continue with Google ·
                             Continue with Microsoft · ── "or sign up with email" ──
                             Email + Password (8+ chars, visibility toggle)
  │  email path
  ▼
/sign-up/verify              6-digit email code (Clerk email_code)
  │
  ▼
POST /auth/complete-signup   Atomic: role + dob + tos_accepted_at + parent_email?
  │  (payload from signed pending_signup cookie — survives OAuth round-trip)
  ▼
/onboarding                  Learner: grade + subjects · Teacher: school/subject · Parent: link-child code
  │
  ▼
/v2/overview                 Role dashboard (existing dispatcher)
```

Every step: "← Choose a different role" back link to `/sign-up`; 180ms
`framer-motion` slide/fade between steps; step dots where >1 step.

### 5.2 Login (slimmed)

`/login` becomes sign-in only: Google · Microsoft · email/password · "Forgot password?"
link · "New here? Create an account" → `/sign-up`. No register toggle, no claim step.

### 5.3 Password recovery (new)

`/forgot-password`: email → Clerk `reset_password_email_code` → code + new password →
`/login`. Uses existing `FormField`/`FieldError` patterns.

### 5.4 OAuth callback

`/sso-callback` keeps `clerk.handleRedirectCallback` + 12s watchdog, but routes via the
canonical resolver instead of inline logic (§6.3).

## 6. Architecture

### 6.1 Route map (dashboard)

New `(auth)` route group with its own minimal centered layout on **light v2 tokens**:

```
dashboard/src/app/
├── (marketing)/page.tsx                      landing (enhanced, §8)
├── (auth)/layout.tsx                         NEW — centered card shell, light v2, logo, locale switcher
│   ├── login/page.tsx                        REWRITE — sign-in only
│   ├── sign-up/page.tsx                      NEW — role selection (honors ?role=)
│   ├── sign-up/learner/page.tsx              NEW — DOB selects
│   ├── sign-up/learner/consent/page.tsx      NEW — under-13 parent email
│   ├── sign-up/account/page.tsx              NEW — ToS + OAuth + email/password
│   ├── sign-up/verify/page.tsx               NEW — email code
│   ├── onboarding/page.tsx                   NEW — per-role profile completion
│   ├── forgot-password/page.tsx              NEW — Clerk reset flow
│   └── sso-callback/page.tsx                 MOVED from (marketing); uses resolver
└── (dashboard)/…                             unchanged
```

Delete: `(marketing)/login/page.tsx`, `(marketing)/sign-in/page.tsx`,
`(marketing)/sign-up/page.tsx` re-exports. `middleware.ts` public-route matcher updated:
`/`, `/login(.*)`, `/sign-up(.*)`, `/forgot-password(.*)`, `/sso-callback(.*)`,
`/auth(.*)`, `/api(.*)`. `/sign-in(.*)` kept as a redirect to `/login` (external links
may reference it).

### 6.2 Role transport: signed `pending_signup` cookie

Role/DOB are chosen **before** OAuth, so they must survive the redirect round-trip.

- Cookie `pending_signup`: `{ role, dob?, tos_accepted_at, parent_email? }`, HMAC-signed
  (server-side via a small `/auth/signup-intent` endpoint that sets it; value never
  trusted from client raw), `HttpOnly; Secure; SameSite=Lax`, 30-min TTL.
- OAuth is same-origin → cookie survives. `/sso-callback` → resolver sees pending intent
  → `POST /auth/complete-signup` consumes it (single-use; cleared on success/expiry).
- Email/password path sets the same cookie at the account step for one code path.

### 6.3 Canonical post-auth resolver

```ts
// dashboard/src/lib/auth/resolveDestination.ts — single source of truth
export function resolvePostAuthDestination(
  me: AuthMe,               // GET /auth/me shape (extended, §6.4)
  requestedNext?: string,   // ?next= / ?redirect_url=
): string
// role_claimed === false        → /sign-up            (resume at role step)
// me.onboarding_completed false → /onboarding
// else → safeNextPath(requestedNext) ?? '/v2/overview'
```

Consumed by: `sso-callback`, `login`, `sign-up/verify`. `safeNextPath` unchanged.
`middleware.ts` stays the coarse gate; `fetchWithAuth` 401 behavior unchanged.

### 6.4 Backend changes (`src/`)

**Migration** (Alembic, `users` table):

| Column | Type | Notes |
|---|---|---|
| `date_of_birth` | `Date`, null | learners |
| `tos_accepted_at` | `DateTime(tz)`, null | all web users |
| `parent_email` | `String(255)`, null | under-13 learners |
| `onboarding_completed_at` | `DateTime(tz)`, null | set by `/auth/onboarding` |

**Endpoints** (`src/api/auth.py`):

| Method | Path | Auth | Body → behavior |
|---|---|---|---|
| POST | `/auth/signup-intent` | none | `{role, dob?, tos_accepted, parent_email?}` → validate (role in learner/teacher/parent; dob required for learner; parent_email required if age < 13) → set signed `pending_signup` cookie |
| POST | `/auth/complete-signup` | Bearer | reads `pending_signup` → validate cookie (sig, TTL, single-use) → set `role`, `role_claimed=True`, `date_of_birth`, `tos_accepted_at`, `parent_email`; if age < 13 → `is_active=False` + enqueue consent notice to parent email (log-only until email provider confirmed) → clear cookie. 409 if `role_claimed` already. |
| POST | `/auth/onboarding` | Bearer | learner: `{grade_level: 7–12, subjects: [...]}`; teacher: `{subject, school?}`; parent: `{child_link_code}` → writes fields, sets `onboarding_completed_at`. **First writer of `User.grade_level`.** |
| GET | `/auth/me` | Bearer | response extended: `grade_level`, `subject`, `date_of_birth`, `onboarding_completed: bool`, `role_claimed` (existing) |

- `MIN_SELF_CONSENT_AGE = 13` in `src/config.py` (env-overridable).
- `POST /auth/claim-role` **kept** for backward compat during cutover; marked deprecated,
  removed in a follow-up release once new flow is live.
- Age math is server-side (never trust client-computed age).

### 6.5 Security notes

- `pending_signup` is HMAC-signed + HttpOnly; client never sets it directly.
- Under-13 accounts are `is_active=False` until consent → `get_current_user`'s existing
  active check (`src/api/auth.py:65-81`) enforces the lock everywhere automatically.
- No role/PII added to Clerk metadata; identity of record stays in our DB.
- Out of scope but tracked: workspace API auth (§3), Telegram linking (§3).

## 7. Design system work

### 7.1 Theme assignment

- `(auth)` route group → **light v2 tokens** (`--v2-bg #FAFAFA`, surface `#FFFFFF`,
  accent `#14B8A6`, borders `--v2-border`). Layout: centered card (max-w ~440px),
  EthioSci wordmark, locale switcher, minimal footer (ToS/Privacy).
- `(marketing)` stays dark Verge. The seam is intentional: reading vs doing.

### 7.2 Fonts (bug fix — declared but never loaded)

Add `next/font` in root layout:

| Font | Role | Variable |
|---|---|---|
| Inter | body | `--font-inter` |
| Spectral | display/headings | `--font-spectral` |
| JetBrains Mono | labels/code (Verge labels) | `--font-jbmono` |
| Noto Sans Ethiopic | `am` locale | `--font-ethiopic` |

Wire variables into `globals.css` body stack + `tailwind.config.js` `fontFamily`.
Verify with Playwright screenshot diff (fonts currently fall back silently).

### 7.3 New primitives (`dashboard/src/components/ui/`)

| Component | Notes |
|---|---|
| `Accordion` | FAQ + consent details; keyboard-navigable, `aria-expanded` |
| `Dialog` | Generic modal (none exists today; command palette is inline) |
| `OAuthButton` | Google/Microsoft logos, loading state, full-width + compact variants |
| `FormField` | label + input + `required` annotation + `FieldError` wiring |
| `Select` | Month/Day/Year dropdowns (native `<select>` styled, a11y-first) |
| `StepDots` | wizard progress indicator |

All on v2 tokens, `framer-motion` 150–180ms `cubic-bezier(0.16,1,0.3,1)` (matches Verge
motion spec), en/am strings via `next-intl`.

## 8. Landing page enhancement & polish

All work in `dashboard/src/app/(marketing)/` — dark Verge theme retained.

| # | Change | Detail |
|---|---|---|
| L1 | **Teacher banner** | Dismissible slim banner above header: "More for teachers: assign practice, track progress — **Sign up free**" → `/sign-up?role=teacher`. Dismissal persisted in localStorage (`ethiosci_banner_teacher_dismissed`). Khan pattern. |
| L2 | **Hero CTAs** | Primary: "Start learning" → `/sign-up?role=learner`. Secondary: "Try on Telegram" (**kept**, quieted to ghost style) → `t.me/ethiobio_bot`. Tertiary text link: "Log in". |
| L3 | **Role panels** | Student/Teacher/Parent cards deep-link to `/sign-up?role={role}`. |
| L4 | **FAQ section** | New `#faq` before footer: `Accordion`, 8 Q&As (§8.1), `FAQPage` JSON-LD, en + am. Footer nav gains "FAQ" link. |
| L5 | **Footer fixes** | "Login / Verify OTP" → "Log in" → `/login`. Keep "Telegram Bot" link. |
| L6 | **Console honesty** | Teacher tab is a `setTimeout` fake — label all three tabs "Demo" and add a caption "Interactive demo — responses simulated". |
| L7 | **Perf** | Split the 620-line client component: server shell + lazy-loaded `ConsoleTabs`/`StatsSection` below the fold (`next/dynamic`). |
| L8 | **SEO** | Page metadata + OG tags (title/desc/image), `Organization` + `FAQPage` JSON-LD, `sitemap.ts`. |
| L9 | **A11y pass** | Focus-visible rings on Verge mint, accordion ARIA, contrast check `#949494` on `#131313` (bump to `#a8a8a8` if < 4.5:1), reduced-motion respect for framer animations. |

### 8.1 FAQ content (source of truth: `messages/{en,am}.json`)

1. Is EthioSci free? — Yes for learners; sustained by grants/supporters (honest Khan-style framing).
2. Which subjects and grades? — Biology, chemistry, physics, mathematics; Grades 7–12, Ethiopian curriculum.
3. Do you support Amharic? — Yes, UI + answers in Amharic and English.
4. How does EthioSci work on Telegram? — `@ethiobio_bot`: ask questions, quizzes, low-bandwidth friendly.
5. Where do answers come from? — Ethiopian textbooks, with citations; answers grounded in the curriculum.
6. What do teachers get? — Lesson-plan copilot, practice assignment, progress tracking.
7. How does adaptive quizzing work? — Difficulty adapts per student (IRT); explanations follow every answer.
8. How is student data handled? — Minimal data, no ads, DOB used only for age-appropriate experience.

Amharic translations land in the same PR (no English-only launch).

## 9. i18n

- All new pages/sections add keys to `messages/en.json` + `messages/am.json`.
- Copy style: Khan's directness ("Sign up as a learner today!", "required" annotations).
- `html[lang='am']` line-height rule already exists (`globals.css:48-50`); Noto Sans
  Ethiopic ensures correct glyph rendering.

## 10. Testing

**Backend** (`pytest tests/ -v -k "not slow"`):
- `complete-signup`: valid/invalid/expired/tampered cookie; 409 on re-claim; under-13 →
  `is_active=False`; age math edge cases (boundary birthdays).
- `onboarding`: per-role validation, `grade_level` 7–12 bounds, idempotency.
- `/auth/me` extended shape.
- Note: rate limiting disabled in tests via conftest Settings override (repo gotcha #7).

**Frontend unit** (Vitest): `resolveDestination` matrix; age-gate util; wizard guards
(missing intent cookie → `/sign-up`); accordion ARIA; `safeNextPath` regression.

**E2E** (Playwright, `dashboard/e2e/`): 3 role paths (email), Google OAuth (mocked),
under-13 consent path, forgot-password, FAQ accordion, teacher-banner dismiss
persistence, `?role=` preselection.

**Visual**: Playwright screenshot — fonts loaded (no system fallback) on `/sign-up`.

## 11. Rollout (5 phases)

| Phase | Scope | Acceptance |
|---|---|---|
| **0 — Foundations** (½d) | next/font; primitives (Accordion, Dialog, OAuthButton, FormField, Select, StepDots); `(auth)` group + layout | Fonts render (screenshot); primitives have stories/tests |
| **1 — Backend** (1d) | Migration; `/auth/signup-intent`, `/auth/complete-signup`, `/auth/onboarding`; extended `/auth/me`; age gate | Backend tests green; `ruff`/`mypy` clean |
| **2 — Signup wizard** (2d) | Role selection; learner DOB + consent; account (ToS + Google/Microsoft + email); verify; resolver | E2E: 3 role paths pass |
| **3 — Login + recovery** (1d) | `/login` slim rewrite; `/forgot-password`; middleware matcher; delete mega-component; `/sign-in` → `/login` redirect | E2E: login, reset, OAuth mock pass |
| **4 — Landing + polish** (1d) | Teacher banner; hero/role-panel CTAs; FAQ (en/am, JSON-LD); footer fix; console labels; perf split; SEO; a11y | E2E landing tests; Lighthouse ≥ 90 a11y |

**Cutover:** new `(auth)` routes deploy alongside old `/login`; flip middleware + landing
CTAs in the same PR; old component deleted in Phase 3 (no dangling re-exports).
**Rollback:** revert dashboard deploy (Vercel) — backend endpoints are additive-only;
`/auth/claim-role` remains until post-cutover cleanup ticket.

## 12. Follow-up tickets (file on GitHub Issues)

1. **[security, urgent]** Add `get_current_user` to all `src/api/workspace.py` endpoints; scope by owner.
2. **[security]** Auth on `PATCH /users/{telegram_id}/language`.
3. **[feature]** Telegram ↔ web account linking (one-time link code from bot).
4. **[feature]** Teacher verification queue (self-declared → `teacher_unverified` subset → admin approve).
5. **[chore]** README/`check_env.py`/`render.yaml`: remove retired `JWT_SECRET`/OTP/OAuth-backend docs+vars.
6. **[feature]** Parental-consent email delivery (needs email provider decision; currently log-only).
7. **[feature]** Donation/sustainability surface (Khan-style), pending payment infra decision.

## 13. Open questions

- Consent delivery: which email provider for parent-consent notices? (`send_email` exists
  but silently returns False without `email_host` — repo gotcha #3.)
- Do we want a `/faq` standalone route later, or is the landing section enough?
- `school` role: keep backend-assigned only, or add a self-serve "school" path later?
