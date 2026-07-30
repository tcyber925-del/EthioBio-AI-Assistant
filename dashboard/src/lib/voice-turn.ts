import { getToken } from './auth'

export async function isVoiceTurnEnabled(): Promise<boolean> {
  try {
    const token = getToken()
    const res = await fetch('/chat/voice/turn', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) return false
    const data = await res.json()
    return data.enabled === true
  } catch {
    return false
  }
}
