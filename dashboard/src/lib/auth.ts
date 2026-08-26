import { setCookie } from './cookies'

let _tokenCache: string | null = null
let _decodedCache: { sub?: string; role?: string } | null = null

function decodeJWT(token: string): { sub?: string; role?: string } | null {
  try {
    const parts = token.split(".")
    if (parts.length !== 3) return null
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")))
    return { sub: payload.sub, role: payload.role }
  } catch {
    return null
  }
}

export function isAuthenticated(): boolean {
  return document.cookie.includes("auth_ready=1")
}

export function getToken(): string | null {
  return _tokenCache
}

export function setToken(token: string): void {
  _tokenCache = token
  _decodedCache = decodeJWT(token)
  setCookie("auth_ready", "1", 1)
  if (_decodedCache?.role) {
    setCookie("user_role", _decodedCache.role, 1)
  }
}

export function clearToken(): void {
  _tokenCache = null
  _decodedCache = null
  document.cookie = "auth_ready=;path=/;max-age=0"
  document.cookie = "user_role=;path=/;max-age=0"
  fetch("/auth/logout", { method: "POST", credentials: "include" })
}

export function decodeToken(): { sub?: string; role?: string } | null {
  return _decodedCache
}

export function getUserId(): string | null {
  return _decodedCache?.sub ?? null
}

export async function initAuth(): Promise<void> {
  if (_tokenCache || _decodedCache) return
  try {
    // Always ask the backend — the client-side auth_ready/user_role cookies are
    // short-lived caches and may be expired while the httpOnly session token
    // (which /auth/me reads) is still valid. A successful response proves the
    // session and lets us refresh those cookies for every consumer.
    const res = await fetch("/auth/me", { credentials: "include" })
    if (!res.ok) return
    const me = await res.json()
    _decodedCache = { sub: me.user_id, role: me.role }
    setCookie("auth_ready", "1", 1)
    if (me.role) {
      setCookie("user_role", me.role, 1)
    }
  } catch {
    // backend unreachable — leave caches empty
  }
}

export function getUserRole(): string {
  if (_decodedCache?.role) return _decodedCache.role
  const match = document.cookie.match(/(?:^|;\s*)user_role=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ""
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
