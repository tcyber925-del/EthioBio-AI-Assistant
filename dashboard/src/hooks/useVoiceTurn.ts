'use client'

import { useRef, useState, useCallback } from 'react'
import type { AudioPlayerHandle } from '@/components/AudioPlayer'
import { voiceTurnFetch } from '@/lib/voice-turn'
import { normalizeException, type AppError } from '@/lib/errors'

export type VoiceTurnState = 'idle' | 'recording' | 'processing' | 'speaking' | 'error'

interface UseVoiceTurnOptions {
  gradeLevel: number
  language: string
  selectedModel?: string
  subject?: string
  onTranscript?: (text: string) => void
  onToken?: (text: string) => void
  onError?: (error: AppError) => void
}

interface UseVoiceTurnReturn {
  audioPlayerRef: React.RefObject<AudioPlayerHandle | null>
  state: VoiceTurnState
  audioLevel: number
  error: AppError | null
  startRecording: () => Promise<void>
  stopRecording: () => void
  stopPlayback: () => void
  reset: () => void
}

export function useVoiceTurn({
  gradeLevel,
  language,
  selectedModel,
  subject,
  onTranscript,
  onToken,
  onError,
}: UseVoiceTurnOptions): UseVoiceTurnReturn {
  const audioPlayerRef = useRef<AudioPlayerHandle | null>(null)
  const [state, setState] = useState<VoiceTurnState>('idle')
  const [audioLevel, setAudioLevel] = useState(0)
  const [error, setError] = useState<AppError | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const rafRef = useRef(0)
  const chunksRef = useRef<Blob[]>([])
  const abortRef = useRef<AbortController | null>(null)

  const cleanupMedia = useCallback(() => {
    cancelAnimationFrame(rafRef.current)
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    mediaRecorderRef.current = null
    analyserRef.current = null
    setAudioLevel(0)
  }, [])

  const startRecording = useCallback(async () => {
    setError(null)
    chunksRef.current = []

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const audioCtx = new AudioContext()
      const source = audioCtx.createMediaStreamSource(stream)
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      const dataArray = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteFrequencyData(dataArray)
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
        setAudioLevel(Math.min(1, avg / 128))
        rafRef.current = requestAnimationFrame(tick)
      }
      rafRef.current = requestAnimationFrame(tick)

      const mimeType = MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/ogg'
      const recorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        cleanupMedia()
        setState('processing')

        const blob = new Blob(chunksRef.current, { type: mimeType })
        if (blob.size === 0) {
          const appErr: AppError = { category: 'client', retryable: false }
          setError(appErr)
          setState('error')
          onError?.(appErr)
          return
        }

        const ctrl = new AbortController()
        abortRef.current = ctrl

        try {
          await voiceTurnFetch(
            blob,
            gradeLevel,
            language,
            selectedModel ?? '',
            {
              onSttTranscript: (text) => {
                onTranscript?.(text)
              },
              onToken: (token) => {
                onToken?.(token)
              },
              onAudio: (b64) => {
                setState('speaking')
                audioPlayerRef.current?.enqueueChunk(b64)
              },
              onError: (err) => {
                setError(err)
                setState('error')
                onError?.(err)
              },
              onDone: () => {
                audioPlayerRef.current?.endStream()
                setState('idle')
              },
            },
            ctrl.signal,
            subject,
          )
        } catch (err: unknown) {
          if (err instanceof DOMException && err.name === 'AbortError') return
          const appErr = normalizeException(err)
          setError(appErr)
          setState('error')
          onError?.(appErr)
        }
      }

      recorder.start()
      setState('recording')
    } catch {
      cleanupMedia()
      setError({ category: 'client', retryable: false })
      setState('error')
      onError?.({ category: 'client', retryable: false })
    }
  }, [gradeLevel, language, selectedModel, cleanupMedia, onTranscript, onToken, onError])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  const stopPlayback = useCallback(() => {
    audioPlayerRef.current?.stop()
    setState('idle')
  }, [])

  const reset = useCallback(() => {
    cleanupMedia()
    audioPlayerRef.current?.stop()
    abortRef.current?.abort()
    setState('idle')
    setError(null)
    setAudioLevel(0)
  }, [cleanupMedia])

  return {
    audioPlayerRef,
    state,
    audioLevel,
    error,
    startRecording,
    stopRecording,
    stopPlayback,
    reset,
  }
}
