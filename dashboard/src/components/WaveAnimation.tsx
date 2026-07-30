'use client'

import { useRef, useEffect } from 'react'

interface WaveAnimationProps {
  audioLevel: number
  source: 'mic' | 'speaker'
  barCount?: number
  className?: string
}

export function WaveAnimation({
  audioLevel,
  source,
  barCount = 7,
  className = '',
}: WaveAnimationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const barsRef = useRef<number[]>(Array(barCount).fill(0))
  const rafRef = useRef(0)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const w = canvas.clientWidth * dpr
    const h = canvas.clientHeight * dpr
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w
      canvas.height = h
    }

    const draw = () => {
      const bars = barsRef.current
      const target = audioLevel * 0.8 + 0.2 * Math.random() * audioLevel

      for (let i = 0; i < bars.length; i++) {
        const base = 0.3 + (i / bars.length) * 0.7
        const targetHeight = target * base
        bars[i] += (targetHeight - bars[i]) * 0.25
        if (bars[i] < 0.01) bars[i] = 0
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const gap = 3 * dpr
      const totalGap = gap * (bars.length - 1)
      const barW = (canvas.width - totalGap) / bars.length

      const color = source === 'speaker' ? '#22c55e' : '#60a5fa'

      for (let i = 0; i < bars.length; i++) {
        const barH = Math.max(2 * dpr, bars[i] * canvas.height)
        const x = i * (barW + gap)
        const y = (canvas.height - barH) / 2

        ctx.fillStyle = color
        ctx.beginPath()
        ctx.roundRect(x, y, barW, barH, 2 * dpr)
        ctx.fill()
      }

      rafRef.current = requestAnimationFrame(draw)
    }

    rafRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(rafRef.current)
  }, [audioLevel, source, barCount])

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ width: '100%', height: '100%', display: 'block' }}
    />
  )
}
