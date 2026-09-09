'use client'

import { fetchWithAuthJson } from '@/lib/fetchWithAuth'
import type { PostAuthMe } from './resolveDestination'

const SWALLOWED_CODES = new Set(['missing_signup_intent', 'role_already_claimed'])

/**
 * Consume the signed `pending_signup` cookie after a Clerk session exists.
 * Returns the updated /auth/me shape, or null when there is no pending intent
 * (expired/absent cookie) or the role was already claimed. Other failures
 * (network, 5xx) propagate so the caller can surface them.
 */
export async function tryCompleteSignup(): Promise<PostAuthMe | null> {
  try {
    return await fetchWithAuthJson<PostAuthMe>('/auth/complete-signup', { method: 'POST' })
  } catch (err) {
    const code = (err as { code?: string } | null)?.code
    if (code && SWALLOWED_CODES.has(code)) return null
    throw err
  }
}

/** POST the wizard's intent to the backend (sets the signed cookie). */
export async function postSignupIntent(body: {
  role: 'student' | 'teacher' | 'parent'
  dob?: string
  parent_email?: string
  tos_accepted: boolean
}): Promise<{ ok: boolean; role: string; requires_parental_consent: boolean }> {
  const res = await fetch('/auth/signup-intent', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    const err = new Error(text || `signup-intent failed (${res.status})`) as Error & {
      code?: string
    }
    try {
      err.code = JSON.parse(text)?.error?.code
    } catch {
      // keep generic message
    }
    throw err
  }
  return res.json()
}
