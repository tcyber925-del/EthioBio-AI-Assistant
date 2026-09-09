'use client'

/**
 * Wizard-local draft of the signup intent (role is also mirrored in the URL).
 * sessionStorage keeps DOB / parent email out of the URL and browser history.
 * Server-verified truth lives in the signed `pending_signup` cookie set by
 * POST /auth/signup-intent — this draft only drives the wizard UI between
 * steps and survives the same-tab OAuth round-trip.
 */

const STORAGE_KEY = 'ethiosci_signup_intent'

export type SignupRole = 'student' | 'teacher' | 'parent'

export interface SignupIntentDraft {
  role: SignupRole
  dob?: string // YYYY-MM-DD (learners only)
  parentEmail?: string // under-13 learners only
}

/** Normalizes ?role= values; "learner" is the public term, backend uses "student". */
export function normalizeRole(raw: string | null | undefined): SignupRole | null {
  if (raw === 'learner' || raw === 'student') return 'student'
  if (raw === 'teacher' || raw === 'parent') return raw
  return null
}

export function saveSignupIntent(draft: SignupIntentDraft): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(draft))
  } catch {
    // storage unavailable (private mode) — wizard degrades to single-session flow
  }
}

export function loadSignupIntent(): SignupIntentDraft | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<SignupIntentDraft>
    const role = normalizeRole(parsed.role)
    return role ? { role, dob: parsed.dob, parentEmail: parsed.parentEmail } : null
  } catch {
    return null
  }
}

export function clearSignupIntent(): void {
  if (typeof window === 'undefined') return
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}

/** Whole years between a YYYY-MM-DD date of birth and today (local time). */
export function ageFromDob(dob: string): number {
  const [y, m, d] = dob.split('-').map(Number)
  if (!y || !m || !d) return -1
  const today = new Date()
  let age = today.getFullYear() - y
  if (today.getMonth() + 1 < m || (today.getMonth() + 1 === m && today.getDate() < d)) {
    age -= 1
  }
  return age
}
