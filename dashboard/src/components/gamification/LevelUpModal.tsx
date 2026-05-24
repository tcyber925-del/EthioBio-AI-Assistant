'use client'

import { useEffect, useState } from 'react'
import { X, TrendingUp } from 'lucide-react'

interface LevelUpModalProps {
  level: number
  onClose: () => void
}

export default function LevelUpModal({ level, onClose }: LevelUpModalProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 50)
    return () => clearTimeout(t)
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className={`absolute inset-0 bg-black/60 transition-opacity duration-300 ${visible ? 'opacity-100' : 'opacity-0'}`}
        onClick={onClose}
      />
      <div
        className={`relative bg-card border border-border rounded-2xl p-8 max-w-sm w-full mx-4 text-center transition-all duration-300 ${
          visible ? 'scale-100 opacity-100' : 'scale-75 opacity-0'
        }`}
      >
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-1 text-foreground-muted hover:text-foreground transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex justify-center mb-4">
          <div className="p-3 rounded-full bg-yellow-500/20 animate-bounce">
            <TrendingUp className="w-10 h-10 text-yellow-400" />
          </div>
        </div>

        <h2 className="text-2xl font-bold text-foreground mb-2">Level Up!</h2>
        <p className="text-foreground-muted mb-1">You&apos;ve reached</p>
        <p className="text-5xl font-extrabold text-yellow-400 mb-2">Level {level}</p>
        <p className="text-sm text-foreground-muted">Keep learning to unlock more rewards!</p>
      </div>
    </div>
  )
}
