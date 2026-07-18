const DEFAULT_TIMEOUT = 30000

export async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)
  try {
    const cacheBust = url.includes('?') ? `${url}&_t=${Date.now()}` : `${url}?_t=${Date.now()}`
    const res = await fetch(cacheBust, { ...options, signal: controller.signal })
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
