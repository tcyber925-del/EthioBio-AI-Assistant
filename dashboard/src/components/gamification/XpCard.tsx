'use client'

import { Award } from 'lucide-react'

interface XpCardProps {
  totalXp: number
  level: number
  nextLevelXp: number
  progressPct: number
}

export default function XpCard({ totalXp, level, nextLevelXp, progressPct }: XpCardProps) {
  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-yellow-500/10 text-yellow-400">
          <Award className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-foreground-muted">XP & Level</p>
          <p className="text-lg font-bold text-foreground">Level {level}</p>
        </div>
      </div>
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="text-foreground-muted">{totalXp.toLocaleString()} XP</span>
        <span className="text-foreground-muted">{nextLevelXp.toLocaleString()} XP to next level</span>
      </div>
      <div className="w-full bg-border rounded-full h-2.5">
        <div
          className="bg-yellow-400 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(progressPct, 100)}%` }}
        />
      </div>
    </div>
  )
}
