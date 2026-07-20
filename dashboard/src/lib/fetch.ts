import { getToken } from './auth'

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

export interface StreamChunk {
  delta: string
  node: string
  done: boolean
  error: string | null
  status: boolean
  metadata?: Record<string, unknown>
}

export type StreamCallbacks = {
  onStatus?: (status: string) => void
  onToken?: (token: string) => void
  onMetadata?: (metadata: Record<string, unknown>) => void
  onError?: (error: string) => void
  onDone?: () => void
}

export async function streamFetch(
  url: string,
  body: Record<string, unknown>,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
) {
  const token = getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify({ ...body, stream: true }),
    signal,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    try {
      const json = JSON.parse(text)
      callbacks.onError?.(json.detail || json.error || `HTTP ${res.status}`)
    } catch {
      callbacks.onError?.(text || `HTTP ${res.status}`)
    }
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    callbacks.onError?.('No response body')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const chunk: StreamChunk = JSON.parse(line.slice(6))
        if (chunk.error) {
          callbacks.onError?.(chunk.error)
          return
        }
        if (chunk.status) {
          callbacks.onStatus?.(chunk.delta)
        } else if (chunk.delta) {
          callbacks.onToken?.(chunk.delta)
        }
        if (chunk.metadata) {
          callbacks.onMetadata?.(chunk.metadata)
        }
        if (chunk.done) {
          callbacks.onDone?.()
          return
        }
      } catch {
        // skip malformed SSE lines
      }
    }
  }
}
