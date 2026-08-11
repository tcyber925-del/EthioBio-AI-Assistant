'use client'

import { useRef, useCallback, useEffect, forwardRef, useImperativeHandle } from 'react'
import type { AppError } from '@/lib/errors'

export interface AudioPlayerHandle {
  enqueueChunk: (base64Mp3: string) => void
  endStream: () => void
  stop: () => void
}

interface AudioPlayerProps {
  onStateChange?: (state: 'idle' | 'playing') => void
  onError?: (error: AppError) => void
}

const MIME_TYPE = 'audio/mpeg'

export const AudioPlayer = forwardRef<AudioPlayerHandle, AudioPlayerProps>(
  function AudioPlayer({ onStateChange, onError }, ref) {
  const mediaSourceRef = useRef<MediaSource | null>(null)
  const sourceBufferRef = useRef<SourceBuffer | null>(null)
  const queueRef = useRef<Uint8Array[]>([])
  const endedRef = useRef(false)
  const streamEndedRef = useRef(false)
  const stateRef = useRef<'idle' | 'playing'>('idle')
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const setUpdatingGuard = useRef(false)

  const setState = useCallback(
    (next: 'idle' | 'playing') => {
      if (stateRef.current === next) return
      stateRef.current = next
      onStateChange?.(next)
    },
    [onStateChange],
  )

  const appendChunk = useCallback((data: Uint8Array) => {
    const sb = sourceBufferRef.current
    if (!sb) {
      queueRef.current.push(data)
      return
    }
    if (sb.updating) {
      queueRef.current.push(data)
      return
    }
    try {
      sb.appendBuffer(data.buffer as ArrayBuffer)
    } catch {
      queueRef.current.push(data)
    }
  }, [])

  const drainQueue = useCallback(() => {
    if (setUpdatingGuard.current) return
    const sb = sourceBufferRef.current
    if (!sb || sb.updating) return
    const q = queueRef.current
    if (q.length === 0) {
      if (streamEndedRef.current && endedRef.current) {
        setState('idle')
      }
      return
    }
      setUpdatingGuard.current = true
    try {
      const chunk = q.shift()!
      sb.appendBuffer(chunk.buffer as ArrayBuffer)
    } catch {
      setUpdatingGuard.current = false
      drainQueue()
    }
  }, [setState])

  const enqueueChunk = useCallback(
    (base64Mp3: string) => {
      const binary = atob(base64Mp3)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i)
      }
      endedRef.current = false
      appendChunk(bytes)
      if (stateRef.current === 'idle') {
        setState('playing')
      }
    },
    [appendChunk, setState],
  )

  const endStream = useCallback(() => {
    streamEndedRef.current = true
    if (queueRef.current.length === 0 && endedRef.current) {
      setState('idle')
    }
  }, [setState])

  const stop = useCallback(() => {
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
    queueRef.current = []
    streamEndedRef.current = false
    endedRef.current = false
    setState('idle')
  }, [setState])

  useEffect(() => {
    const audio = new Audio()
    audioRef.current = audio

    const ms = new MediaSource()
    mediaSourceRef.current = ms

    ms.addEventListener('sourceopen', () => {
      const sb = ms.addSourceBuffer(MIME_TYPE)
      sourceBufferRef.current = sb

      sb.addEventListener('updateend', () => {
        setUpdatingGuard.current = false
        endedRef.current = sb.buffered.length > 0
        if (ms.readyState === 'ended' && queueRef.current.length === 0) {
          setState('idle')
          return
        }
        drainQueue()
      })

      sb.addEventListener('error', () => {
        onError?.({ category: 'client', retryable: false })
      })

      for (const chunk of queueRef.current) {
        try {
          sb.appendBuffer(chunk.buffer as ArrayBuffer)
        } catch {
          break
        }
      }
      queueRef.current = []
    })

    ms.addEventListener('sourceended', () => {
      setState('idle')
    })

    ms.addEventListener('error', () => {
      onError?.({ category: 'client', retryable: false })
    })

    audio.addEventListener('ended', () => {
      if (streamEndedRef.current && queueRef.current.length === 0) {
        setState('idle')
      }
    })

    audio.addEventListener('error', () => {
      onError?.({ category: 'client', retryable: false })
    })

    const url = URL.createObjectURL(ms)
    audio.src = url

    audio.play().catch(() => {
      // browser may block autoplay — will be handled by user gesture
    })

    return () => {
      stop()
      if (url) URL.revokeObjectURL(url)
      if (ms.readyState !== 'closed') {
        try {
          ms.endOfStream()
        } catch {
          // already ended
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useImperativeHandle(ref, () => ({ enqueueChunk, endStream, stop }), [enqueueChunk, endStream, stop])

  return null
  },
)
