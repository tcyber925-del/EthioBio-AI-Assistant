'use client'

import { useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Mic, Loader2 } from 'lucide-react'
import { getToken, getUserId } from '@/lib/auth'
import { normalizeException, normalizeHttpError, type AppError } from '@/lib/errors'

type VoiceState = 'idle' | 'recording' | 'processing'

interface VoiceRecorderButtonProps {
  onTranscript: (text: string) => void
  onPartialTranscript?: (text: string) => void
  onError?: (error: AppError) => void
  disabled?: boolean
  gradeLevel?: number
  topic?: string
  language?: string
  streaming?: boolean
}

export function VoiceRecorderButton({
  onTranscript,
  onPartialTranscript,
  onError,
  disabled,
  gradeLevel,
  topic,
  language = 'am',
  streaming,
}: VoiceRecorderButtonProps) {
  const ta = useTranslations('ask')
  const [state, setState] = useState<VoiceState>('idle')
  const [audioLevel, setAudioLevel] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamSessionIdRef = useRef('')
  const isSendingRef = useRef(false)
  const animFrameRef = useRef(0)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const onTranscriptRef = useRef(onTranscript)
  const onPartialTranscriptRef = useRef(onPartialTranscript)
  const onErrorRef = useRef(onError)
  onTranscriptRef.current = onTranscript
  onPartialTranscriptRef.current = onPartialTranscript
  onErrorRef.current = onError

  const stopTracks = () => {
    cancelAnimationFrame(animFrameRef.current)
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
  }

  const sendChunk = async (blob: Blob, isFinal: boolean) => {
    if (isSendingRef.current && !isFinal) return
    isSendingRef.current = true
    const token = getToken()
    const userId = getUserId()
    const formData = new FormData()
    formData.append('audio', blob, 'voice.webm')
    formData.append('stream_session_id', streamSessionIdRef.current)
    formData.append('language', language)
    formData.append('final', String(isFinal))
    if (topic) formData.append('topic', topic)
    if (gradeLevel) formData.append('grade_level', String(gradeLevel))
    if (userId) formData.append('user_id', userId)

    try {
      const res = await fetch('/chat/voice/chunk', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      if (!res.ok) {
        const text = await res.text().catch(() => '')
        throw normalizeHttpError(res.status, text)
      }
      const data = await res.json()
      if (data.partial_transcript) {
        onPartialTranscriptRef.current?.(data.partial_transcript)
      }
      if (data.final_transcript) {
        onTranscriptRef.current(data.final_transcript)
      }
    } catch (err) {
      if (isFinal) {
        onErrorRef.current?.(normalizeException(err))
      }
    } finally {
      isSendingRef.current = false
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
        throw normalizeHttpError(res.status, text)
      }
      const data = await res.json()
      if (data.transcript) onTranscriptRef.current(data.transcript)
    } catch (err) {
      onErrorRef.current?.(normalizeException(err))
    }
  }

  const updateAudioLevel = () => {
    if (!analyserRef.current) return
    const data = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(data)
    const avg = data.reduce((a, b) => a + b, 0) / data.length
    setAudioLevel(Math.min(avg / 128, 1))
    animFrameRef.current = requestAnimationFrame(updateAudioLevel)
  }

  const startRecording = async () => {
    try {
      setAudioLevel(0)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []
      streamSessionIdRef.current = crypto.randomUUID()
      isSendingRef.current = false

      if (streaming) {
        const audioCtx = new AudioContext()
        audioContextRef.current = audioCtx
        const source = audioCtx.createMediaStreamSource(stream)
        const analyser = audioCtx.createAnalyser()
        analyser.fftSize = 256
        source.connect(analyser)
        analyserRef.current = analyser
        updateAudioLevel()
      }

      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          if (streaming) {
            sendChunk(e.data, false)
          } else {
            chunksRef.current.push(e.data)
          }
        }
      }

      recorder.onstop = async () => {
        stopTracks()
        setState('processing')
        if (streaming) {
          if (chunksRef.current.length > 0) {
            await sendChunk(new Blob(chunksRef.current), true)
            chunksRef.current = []
          }
        } else if (chunksRef.current.length > 0) {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm;codecs=opus' })
          await sendAudio(blob)
        }
        setState('idle')
      }

      recorder.onerror = () => {
        stopTracks()
        setState('idle')
        onErrorRef.current?.({ category: 'client', retryable: false })
      }

      recorder.start(streaming ? 1000 : undefined)
      setState('recording')
    } catch {
      stopTracks()
      setState('idle')
      onErrorRef.current?.({ category: 'client', retryable: false })
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }

  const isProcessing = state === 'processing'
  const isRecording = state === 'recording'

  return (
    <button
      onClick={isRecording ? stopRecording : startRecording}
      disabled={disabled || isProcessing}
      title={ta('voice_button')}
      className={`p-3 rounded-lg transition-colors shrink-0 relative ${
        isRecording
          ? 'bg-red-500 text-white hover:bg-red-600'
          : isProcessing
            ? 'bg-v2-bg text-v2-text-muted cursor-not-allowed'
            : 'bg-v2-surface text-v2-text-muted hover:text-v2-text-primary hover:border-v2-border border border-transparent'
      }`}
    >
      {isRecording && (
        <div className="absolute inset-0 flex items-center justify-center gap-[2px] px-2">
          {[0.3, 0.5, 0.7, 0.8, 0.7, 0.5, 0.3].map((base, i) => (
            <span
              key={i}
              className="w-[2px] bg-current rounded-full"
              style={{
                height: `${Math.max(3, audioLevel * 28 * base)}px`,
                opacity: 0.9,
              }}
            />
          ))}
        </div>
      )}
      {isProcessing ? (
        <Loader2 className="w-5 h-5 animate-spin" />
      ) : isRecording ? (
        <span className="opacity-0"><Mic className="w-5 h-5" /></span>
      ) : (
        <Mic className="w-5 h-5" />
      )}
    </button>
  )
}
