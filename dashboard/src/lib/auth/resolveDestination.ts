import { safeNextPath } from '@/lib/safeNextPath'

/**
 * Canonical post-auth routing (ADR-0013). The ONLY place that decides where a
 * user lands after sign-in/sign-up. Consumed by login, signup verify, and
 * sso-callback — never duplicate this logic in a page.
 */
export interface PostAuthMe {
  role_claimed?: boolean
  onboarding_completed?: boolean
  is_active?: boolean
}

export const CONSENT_PENDING_PATH = '/sign-up/consent-pending'

export function resolvePostAuthDestination(
  me: PostAuthMe | null,
  requestedNext?: string | null,
): string {
  if (me?.is_active === false) return CONSENT_PENDING_PATH
  if (me?.role_claimed === false) return '/sign-up'
  if (me && me.onboarding_completed === false) return '/onboarding'
  if (requestedNext && typeof window !== 'undefined') {
    const safe = safeNextPath(
      `?next=${encodeURIComponent(requestedNext)}`,
      window.location.origin,
    )
    if (safe) return safe
  }
  return '/v2/overview'
}

/**
 * Like resolvePostAuthDestination, but when fetching /auth/me fails because
 * the account is inactive (under-13 awaiting parental consent), the backend
 * returns 401 `auth_user_inactive` — route to the consent-pending page
 * instead of the default. Any other failure falls through to the default.
 */
export function resolvePostAuthDestinationOr(
  me: PostAuthMe | null,
  failure: unknown,
  requestedNext?: string | null,
): string {
  const code = (failure as { code?: string } | null)?.code
  if (code === 'auth_user_inactive') return CONSENT_PENDING_PATH
  return resolvePostAuthDestination(me, requestedNext)
}

/** Reads ?next= / ?redirect_url= from the current URL (client-only). */
export function requestedNextFromLocation(): string | null {
  if (typeof window === 'undefined') return null
  const params = new URLSearchParams(window.location.search)
  return params.get('next') ?? params.get('redirect_url')
}
