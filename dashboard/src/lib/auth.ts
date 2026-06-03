const TOKEN_KEY = 'ethiobio_token'

export interface AuthUser {
  user_id: string
  email: string
  role: string
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function decodeToken(token: string): Record<string, any> | null {
  try {
    const payload = token.split('.')[1]
    return JSON.parse(atob(payload))
  } catch {
    return null
  }
}

export function isAuthenticated(): boolean {
  const token = getToken()
  if (!token) return false
  const payload = decodeToken(token)
  if (!payload) return false
  const exp = payload.exp as number
  if (Date.now() >= exp * 1000) {
    clearToken()
    return false
  }
  return true
}

export function getUserId(): string | null {
  const token = getToken()
  if (!token) return null
  const payload = decodeToken(token)
  return payload?.sub || null
}
