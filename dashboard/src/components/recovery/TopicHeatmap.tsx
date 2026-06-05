'use client'

import { useTranslations } from 'next-intl'

interface HistoryRecord {
  average_score: number
  recorded_at: string
}

interface TopicHeatmapProps {
  history: Record<string, HistoryRecord[]>
}

interface DayBucket {
  date: string
  scores: number[]
}

export function TopicHeatmap({ history }: TopicHeatmapProps) {
  const t = useTranslations('recovery')
  const dayMap = new Map<string, number[]>()

  for (const records of Object.values(history)) {
    for (const r of records) {
      const date = r.recorded_at.split('T')[0]
      const bucket = dayMap.get(date)
      if (bucket) {
        bucket.push(r.average_score)
      } else {
        dayMap.set(date, [r.average_score])
      }
    }
  }

  const days: DayBucket[] = Array.from(dayMap.entries())
    .map(([date, scores]) => ({ date, scores }))
    .sort((a, b) => a.date.localeCompare(b.date))

  if (days.length < 2) {
    return (
      <div className="flex items-center justify-center h-24 text-foreground-muted text-sm">
        {t('progress_heatmap_desc')}
      </div>
    )
  }

  const maxAvg = Math.max(...days.map(d => d.scores.reduce((s, x) => s + x, 0) / d.scores.length), 1)

  const getColor = (mastery: number) => {
    const ratio = mastery / maxAvg
    if (ratio < 0.25) return 'bg-red-500/20'
    if (ratio < 0.5) return 'bg-orange-500/30'
    if (ratio < 0.75) return 'bg-yellow-500/40'
    return 'bg-green-500/40'
  }

  const dayFromDate = (date: string) => {
    const parts = date.split('-')
    return parseInt(parts[2], 10)
  }

  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {days.slice(-28).map(p => {
          const avg = p.scores.reduce((s, x) => s + x, 0) / p.scores.length
          return (
            <div
              key={p.date}
              className={`w-6 h-6 rounded ${getColor(avg)} flex items-center justify-center text-[9px] text-foreground-muted cursor-default`}
              title={`${p.date}: ${avg.toFixed(0)}%`}
            >
              {dayFromDate(p.date)}
            </div>
          )
        })}
      </div>
      <div className="flex items-center gap-2 mt-2 text-xs text-foreground-muted">
        <span>{t('heatmap_less')}</span>
        <div className="w-3 h-3 rounded bg-red-500/20" />
        <div className="w-3 h-3 rounded bg-orange-500/30" />
        <div className="w-3 h-3 rounded bg-yellow-500/40" />
        <div className="w-3 h-3 rounded bg-green-500/40" />
        <span>{t('heatmap_more')}</span>
        <span className="ml-auto">{t('last_28_days')}</span>
      </div>
    </div>
  )
}
