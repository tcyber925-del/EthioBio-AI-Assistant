import { setCookie } from './cookies'

let _userIdCache: string | null = null
let _roleCache: string | null = null

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

function readSessionToken(): string | null {
  return readCookie('__session')
}

export function isAuthenticated(): boolean {
  return readSessionToken() !== null
}

export function getToken(): string | null {
  return readSessionToken()
}

export function getUserId(): string | null {
  if (_userIdCache) return _userIdCache
  return readCookie('user_id')
}

export async function initAuth(): Promise<void> {
  if (_userIdCache) return
  try {
    const token = getToken()
    const res = await fetch('/auth/me', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include',
    })
    if (!res.ok) return
    const me = await res.json()
    _userIdCache = me.user_id
    _roleCache = me.role
    setCookie('user_id', me.user_id, 1)
    if (me.role) {
      setCookie('user_role', me.role, 1)
    }
  } catch {
    // backend unreachable — leave caches empty
  }
}

export function getUserRole(): string {
  if (_roleCache) return _roleCache
  return readCookie('user_role') ?? ''
}

/**
 * Resolve the current role, transparently recovering it from /auth/me when the
 * cached cookie is missing or expired. Use this in effects instead of reading
 * getUserRole() synchronously during render.
 */
export async function ensureUserRole(): Promise<string> {
  const existing = getUserRole()
  if (existing) return existing
  await initAuth()
  return getUserRole()
}

export function clearToken(): void {
  _userIdCache = null
  _roleCache = null
  document.cookie = 'user_role=;path=/;max-age=0'
  document.cookie = 'user_id=;path=/;max-age=0'
  const clerk = (window as unknown as { Clerk?: { signOut: () => Promise<unknown> } }).Clerk
  clerk?.signOut().catch(() => undefined)
}