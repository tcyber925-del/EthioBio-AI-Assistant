import { getToken } from './auth'
import { normalizeHttpError, normalizeStreamError } from './errors'
import type { AppError } from './errors'

const DEFAULT_TIMEOUT = 30000

export async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeout)
  try {
    const token = getToken()
    const headers: Record<string, string> = {
      ...((options.headers as Record<string, string>) ?? {}),
    }
    delete headers['Authorization']
    if (token) headers['Authorization'] = `Bearer ${token}`
    const cacheBust = url.includes('?') ? `${url}&_t=${Date.now()}` : `${url}?_t=${Date.now()}`
    const res = await fetch(cacheBust, { ...options, headers, credentials: 'include', signal: controller.signal })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw normalizeHttpError(res.status, text)
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
  audio_b64?: string
}

export type StreamCallbacks = {
  onStatus?: (status: string) => void
  onToken?: (token: string) => void
  onAudio?: (base64: string) => void
  onMetadata?: (metadata: Record<string, unknown>) => void
  onError?: (error: AppError) => void
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
    credentials: 'include',
    body: JSON.stringify({ ...body, stream: true }),
    signal,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    callbacks.onError?.(normalizeHttpError(res.status, text))
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    callbacks.onError?.({ category: 'service', code: 'no_response_body', retryable: true })
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
          callbacks.onError?.(normalizeStreamError(chunk.error))
          return
        }
        if (chunk.audio_b64) {
          callbacks.onAudio?.(chunk.audio_b64)
          continue
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
