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

export interface VoiceTurnCallbacks {
  onSttTranscript?: (transcript: string) => void
  onToken?: (token: string) => void
  onAudio?: (base64: string) => void
  onMetadata?: (metadata: Record<string, unknown>) => void
  onError?: (error: string) => void
  onDone?: () => void
}

export async function voiceTurnFetch(
  audioBlob: Blob,
  gradeLevel: number,
  language: string,
  selectedModel: string,
  callbacks: VoiceTurnCallbacks,
  signal?: AbortSignal,
) {
  const token = getToken()
  const form = new FormData()
  form.append('audio', audioBlob, `recording.${audioBlob.type === 'audio/webm' ? 'webm' : 'ogg'}`)
  form.append('grade_level', String(gradeLevel))
  form.append('language', language)
  if (selectedModel) form.append('model', selectedModel)

  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch('/chat/voice/turn', {
    method: 'POST',
    headers,
    body: form,
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
        const chunk = JSON.parse(line.slice(6)) as {
          delta: string
          node: string
          done: boolean
          error: string | null
          status: boolean
          metadata?: Record<string, unknown>
          audio_b64?: string
        }

        if (chunk.error) {
          callbacks.onError?.(chunk.error)
          return
        }

        if (chunk.node === 'stt' && chunk.metadata?.transcript) {
          callbacks.onSttTranscript?.(chunk.metadata.transcript as string)
          continue
        }

        if (chunk.audio_b64) {
          callbacks.onAudio?.(chunk.audio_b64)
          continue
        }

        if (chunk.status && chunk.delta) {
          // status event — skip for voice flow
          continue
        }

        if (chunk.delta && !chunk.done) {
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
