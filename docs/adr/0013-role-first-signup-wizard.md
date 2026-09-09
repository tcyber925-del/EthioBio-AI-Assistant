# ADR-0013: Role-First, URL-Driven Signup Wizard with Signed `pending_signup` Cookie

## Status

Accepted

## Context

The pre-redesign auth flow put role selection **last**: every Clerk signup was
auto-provisioned as `student`, then self-declared a role via `POST /auth/claim-role`,
with OAuth users bounced back to `/login?role_claim=1` to pick one. The entire flow —
sign-in, register, email verification, role claim — lived in a single 300-line
`useState` component (`(marketing)/login/page.tsx`), which made steps non-deep-linkable,
broke the back button, and scattered post-auth redirect logic across four files
(`login`, `sso-callback`, `middleware.ts`, `fetchWithAuth`).

Khan Academy's flow inverts this: **role is the entry point** ("Sign up as a
learner/parent/teacher"), each step is a page, and learners get an age-appropriate path
(DOB collection before account creation). We wanted that UX, but Clerk's OAuth redirect
loses client-side state — role/DOB chosen before `authenticateWithRedirect` must survive
the round-trip.

## Decision

1. **Role-first, URL-driven wizard.** Each signup step is a real route under a new
   `(auth)` route group (`/sign-up` → role, `/sign-up/learner` → DOB,
   `/sign-up/account` → credentials, `/sign-up/verify` → email code), not component
   state. Steps are deep-linkable, back-button safe, and individually instrumentable.
2. **Signed `pending_signup` cookie for pre-auth intent.** Role/DOB/ToS are posted to
   `POST /auth/signup-intent`, which validates and stores them in an HMAC-signed,
   `HttpOnly; Secure; SameSite=Lax` cookie (30-min TTL, single-use). Because OAuth is
   same-origin, the cookie survives the redirect; `/sso-callback` then calls
   `POST /auth/complete-signup`, which atomically claims role + stores DOB/ToS.
   Chosen over Clerk `unsafeMetadata` because it is server-verifiable and never
   client-tamperable — acceptable risk for role, but not for DOB/consent data.
3. **One canonical post-auth resolver.** `resolvePostAuthDestination(me, next?)`
   (`src/lib/auth/resolveDestination.ts`) is the only place that decides
   `/sign-up` (role unclaimed) vs `/onboarding` (profile incomplete) vs
   `safeNextPath(next) ?? /v2/overview`. All auth pages call it.
4. **Age gate server-side.** `MIN_SELF_CONSENT_AGE = 13` (config); under-13 learners
   require a parent email and are provisioned `is_active=False` until consent, enforced
   for free by the existing active check in `get_current_user`.

## Consequences

- Backend `users` gains `date_of_birth`, `tos_accepted_at`, `parent_email`,
  `onboarding_completed_at` (migration); `/auth/onboarding` becomes the first real
  writer of the previously dead `User.grade_level`.
- `/auth/claim-role` is kept for backward compatibility during cutover, then removed.
- Under-13 accounts need a consent-delivery mechanism; email provider is an open
  question (tracked in the spec's follow-up tickets).
- Deleting the `/login` mega-component removes the `?role_claim=1` hack; `/sign-in`
  remains only as a redirect to `/login` for external links.
