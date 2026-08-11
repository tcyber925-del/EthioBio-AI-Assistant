'use client'

import { useRef, useState } from 'react'
import { Mic, Loader2, StopCircle } from 'lucide-react'
import { getToken } from '@/lib/auth'
import { normalizeException, normalizeHttpError, type AppError } from '@/lib/errors'

type VoiceState = 'idle' | 'recording' | 'processing'

interface QuizVoiceButtonProps {
  onTranscript: (text: string) => void
  onError?: (error: AppError) => void
  disabled?: boolean
  language?: string
}

export function QuizVoiceButton({
  onTranscript,
  onError,
  disabled,
  language = 'am',
}: QuizVoiceButtonProps) {
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
        onError?.({ category: 'client', retryable: false })
      }

      recorder.start()
      setState('recording')
    } catch {
      setState('idle')
      onError?.({ category: 'client', retryable: false })
    }
  }

  const stopRecording = () => {
    if (mediaRecorder.current && mediaRecorder.current.state === 'recording') {
      mediaRecorder.current.stop()
    }
  }

  const sendAudio = async (blob: Blob) => {
    const token = getToken()
    const formData = new FormData()
    formData.append('audio', blob, 'voice.webm')
    formData.append('language', language)

    try {
      const res = await fetch('/api/quiz/transcribe', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })

      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw normalizeHttpError(res.status, text)
      }

      const data = await res.json()
      if (data.transcript) {
        onTranscript(data.transcript)
      }
    } catch (err) {
      onError?.(normalizeException(err))
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
      title="Voice input"
      className={`p-2 rounded-lg transition-colors shrink-0 ${
        state === 'recording'
          ? 'bg-red-500 text-white animate-pulse'
          : state === 'processing'
            ? 'bg-v2-bg text-v2-text-muted cursor-not-allowed'
            : 'bg-v2-accent/10 text-v2-accent hover:bg-v2-accent/20'
      }`}
    >
      {state === 'processing' ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : state === 'recording' ? (
        <StopCircle className="w-4 h-4" />
      ) : (
        <Mic className="w-4 h-4" />
      )}
    </button>
  )
}
