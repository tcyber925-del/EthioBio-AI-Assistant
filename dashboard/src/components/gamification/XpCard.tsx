'use client'

import { useLocale, useTranslations } from 'next-intl'
import { Award } from 'lucide-react'

interface XpCardProps {
  totalXp: number
  level: number
  nextLevelXp: number
  progressPct: number
}

export default function XpCard({ totalXp, level, nextLevelXp, progressPct }: XpCardProps) {
  const locale = useLocale()
  const tg = useTranslations('gamification')

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-accent-gold/10 text-accent-gold">
          <Award className="w-5 h-5" />
        </div>
        <div>
          <p className="text-small text-foreground-muted">{tg('xp_and_level')}</p>
          <p className="text-heading text-foreground">{tg('level_value', { level })}</p>
        </div>
      </div>
      <div className="mb-2 flex items-center justify-between text-body">
        <span className="text-foreground-muted">{tg('xp_count', { count: totalXp.toLocaleString(locale) })}</span>
        <span className="text-foreground-muted">{tg('xp_to_next_level', { xp: nextLevelXp.toLocaleString(locale) })}</span>
      </div>
      <div className="w-full bg-border rounded-full h-2.5">
        <div
          className="bg-accent-gold h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(progressPct, 100)}%` }}
        />
      </div>
    </div>
  )
}
