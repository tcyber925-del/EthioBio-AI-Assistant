import { setCookie } from './cookies'

let _tokenCache: string | null = null

export function isAuthenticated(): boolean {
  return document.cookie.includes("auth_ready=1")
}

export function getToken(): string | null {
  return _tokenCache
}

export function setToken(token: string): void {
  _tokenCache = token
  setCookie("auth_ready", "1", 1)
}

export function clearToken(): void {
  _tokenCache = null
  document.cookie = "auth_ready=;path=/;max-age=0"
  fetch("/auth/logout", { method: "POST", credentials: "include" })
}

export function decodeToken(): { sub?: string; role?: string } | null {
  return null
}

export function getUserId(): string | null {
  return null
}

export function getUserRole(): string {
  const match = document.cookie.match(/(?:^|;\s*)user_role=([^;]*)/)
  return match ? decodeURIComponent(match[1]) : ""
}
