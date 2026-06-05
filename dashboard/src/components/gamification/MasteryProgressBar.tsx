'use client'

import { useTranslations } from 'next-intl'
import { BarChart3 } from 'lucide-react'

interface MasteryProgressBarProps {
  level: number
  totalXp: number
  nextLevelXp: number
  progressPct: number
}

export default function MasteryProgressBar({ level, totalXp, nextLevelXp, progressPct }: MasteryProgressBarProps) {
  const tg = useTranslations('gamification')

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-green-500/10 text-green-400">
          <BarChart3 className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-foreground-muted">{tg('mastery_progress')}</p>
          <p className="text-lg font-bold text-foreground">{tg('level_value', { level })}</p>
        </div>
        <div className="ml-auto">
          <span className="text-2xl font-bold text-green-400">{Math.round(progressPct)}%</span>
        </div>
      </div>
      <div className="w-full bg-border rounded-full h-3">
        <div
          className="bg-gradient-to-r from-green-500 to-emerald-400 h-3 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(progressPct, 100)}%` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-foreground-muted">
        <span>{tg('xp_earned_label', { xp: totalXp.toLocaleString() })}</span>
        <span>{tg('xp_to_next_level_value', { xp: nextLevelXp.toLocaleString(), level: level + 1 })}</span>
      </div>
    </div>
  )
}
