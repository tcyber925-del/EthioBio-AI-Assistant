'use client'

import { useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Mic, Loader2, StopCircle } from 'lucide-react'
import { getToken, getUserId } from '@/lib/auth'

type VoiceState = 'idle' | 'recording' | 'processing'

interface VoiceRecorderButtonProps {
  onTranscript: (text: string) => void
  onError?: (error: string) => void
  disabled?: boolean
  gradeLevel?: number
  topic?: string
  language?: string
}

export function VoiceRecorderButton({
  onTranscript,
  onError,
  disabled,
  gradeLevel,
  topic,
  language = 'am',
}: VoiceRecorderButtonProps) {
  const ta = useTranslations('ask')
  const [state, setState] = useState<VoiceState>('idle')
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      chunks.current = []
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      mediaRecorder.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        if (chunks.current.length === 0) {
          setState('idle')
          return
        }
        setState('processing')
        const blob = new Blob(chunks.current, { type: 'audio/webm;codecs=opus' })
        await sendAudio(blob)
      }

      recorder.onerror = () => {
        stream.getTracks().forEach(t => t.stop())
        setState('idle')
        onError?.(ta('voice_error'))
      }

      recorder.start()
      setState('recording')
    } catch {
      setState('idle')
      onError?.('Microphone access denied')
    }
  }

  const stopRecording = () => {
    if (mediaRecorder.current && mediaRecorder.current.state === 'recording') {
      mediaRecorder.current.stop()
    }
  }

  const sendAudio = async (blob: Blob) => {
    const token = getToken()
    const userId = getUserId()
    const formData = new FormData()
    formData.append('audio', blob, 'voice.webm')
    formData.append('grade_level', String(gradeLevel ?? ''))
    formData.append('language', language)
    if (topic) formData.append('topic', topic)
    if (userId) formData.append('user_id', userId)

    try {
      const res = await fetch('/chat/voice', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })

      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw new Error(text || `HTTP ${res.status}`)
      }

      const data = await res.json()
      if (data.transcript) {
        onTranscript(data.transcript)
      }
    } catch (err) {
      onError?.(err instanceof Error ? err.message : ta('voice_error'))
    } finally {
      setState('idle')
    }
  }

  const handleClick = () => {
    if (state === 'recording') {
      stopRecording()
    } else {
      startRecording()
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled || state === 'processing'}
      title={ta('voice_button')}
      className={`p-3 rounded-lg transition-colors shrink-0 ${
        state === 'recording'
          ? 'bg-red-500 text-white animate-pulse'
          : state === 'processing'
            ? 'bg-v2-bg text-v2-text-muted cursor-not-allowed'
            : 'bg-v2-surface text-v2-text-muted hover:text-v2-text-primary hover:border-v2-border border border-transparent'
      }`}
    >
      {state === 'processing' ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : state === 'recording' ? (
        <StopCircle className="w-5 h-5" />
      ) : (
        <Mic className="w-5 h-5" />
      )}
    </button>
  )
}
