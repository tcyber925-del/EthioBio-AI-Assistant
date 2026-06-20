'use client'

import { useLocale, useTranslations } from 'next-intl'
import { BarChart3 } from 'lucide-react'

interface MasteryProgressBarProps {
  level: number
  totalXp: number
  nextLevelXp: number
  progressPct: number
}

export default function MasteryProgressBar({ level, totalXp, nextLevelXp, progressPct }: MasteryProgressBarProps) {
  const locale = useLocale()
  const tg = useTranslations('gamification')

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-primary/10 text-primary">
          <BarChart3 className="w-5 h-5" />
        </div>
        <div>
          <p className="text-small text-foreground-muted">{tg('mastery_progress')}</p>
          <p className="text-heading text-foreground">{tg('level_value', { level })}</p>
        </div>
        <div className="ml-auto">
          <span className="text-display text-primary">{Math.round(progressPct)}%</span>
        </div>
      </div>
      <div className="w-full bg-border rounded-full h-3 overflow-hidden">
        <div
          className="bg-gradient-to-r from-primary to-accent-teal h-3 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(progressPct, 100)}%` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-small text-foreground-muted">
        <span>{tg('xp_earned_label', { xp: totalXp.toLocaleString(locale) })}</span>
        <span>{tg('xp_to_next_level_value', { xp: nextLevelXp.toLocaleString(locale), level: level + 1 })}</span>
      </div>
    </div>
  )
}
