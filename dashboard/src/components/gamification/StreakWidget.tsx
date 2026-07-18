'use client'

import { useTranslations } from 'next-intl'
import { Flame } from 'lucide-react'

interface StreakWidgetProps {
  currentStreak: number
  longestStreak: number
}

export default function StreakWidget({ currentStreak, longestStreak }: StreakWidgetProps) {
  const tg = useTranslations('gamification')

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-orange-500/10 text-orange-400">
          <Flame className="w-5 h-5" />
        </div>
        <div>
          <p className="text-small text-foreground-muted">{tg('study_streak')}</p>
          <p className="text-heading text-foreground">{currentStreak} {tg('days')}</p>
        </div>
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between text-body">
          <span className="text-foreground-muted">{tg('current_streak')}</span>
          <span className="text-subhead text-foreground">{currentStreak} {tg('days')}</span>
        </div>
        <div className="h-px bg-border/50" />
        <div className="flex items-center justify-between text-body">
          <span className="text-foreground-muted">{tg('longest_streak')}</span>
          <span className="text-subhead text-foreground">{longestStreak} {tg('days')}</span>
        </div>
      </div>
    </div>
  )
}
