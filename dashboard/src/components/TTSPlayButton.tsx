'use client'

import { useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Volume2, Loader2 } from 'lucide-react'
import { getToken } from '@/lib/auth'

interface TTSPlayButtonProps {
  text: string
  language?: string
}

export function TTSPlayButton({ text, language = 'am' }: TTSPlayButtonProps) {
  const tc = useTranslations('common')
  const [playing, setPlaying] = useState(false)
  const [loading, setLoading] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  const handlePlay = async () => {
    if (playing) {
      audioRef.current?.pause()
      audioRef.current = null
      setPlaying(false)
      return
    }

    setLoading(true)
    try {
      const token = getToken()
      const res = await fetch('/chat/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text, language }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio

      audio.onended = () => {
        URL.revokeObjectURL(url)
        setPlaying(false)
      }
      audio.onerror = () => {
        URL.revokeObjectURL(url)
        setPlaying(false)
      }

      await audio.play()
      setPlaying(true)
    } catch {
      setPlaying(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handlePlay}
      disabled={loading}
      title={tc('play_audio')}
      className={`p-2 rounded-lg transition-colors shrink-0 ${
        playing
          ? 'bg-v2-accent text-v2-inverted'
          : 'bg-v2-accent/10 text-v2-accent hover:bg-v2-accent/20'
      }`}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Volume2 className="w-4 h-4" />
      )}
    </button>
  )
}
