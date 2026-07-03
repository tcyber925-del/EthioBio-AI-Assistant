import { getToken, isAuthenticated } from './auth'

const DEFAULT_TIMEOUT = 30000

export async function fetchWithAuth(url: string, options: RequestInit = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)

  const token = getToken()
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  
  if (typeof window !== 'undefined') {
    const workspaceId = localStorage.getItem('ethiobio_active_workspace_id')
    if (workspaceId) {
      headers['X-Workspace-Id'] = workspaceId
    }
  }

  try {
    const cacheBust = url.includes('?') ? `${url}&_t=${Date.now()}` : `${url}?_t=${Date.now()}`
    const res = await fetch(cacheBust, { ...options, headers, signal: controller.signal })
    if (res.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('ethiobio_token')
      window.location.href = '/login'
      throw new Error('Session expired')
    }
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      try {
        const json = JSON.parse(text)
        throw new Error(json.detail || json.error || `HTTP ${res.status}`)
      } catch {
        throw new Error(text || `HTTP ${res.status}`)
      }
    }
    return await res.json()
  } finally {
    clearTimeout(id)
  }
}
