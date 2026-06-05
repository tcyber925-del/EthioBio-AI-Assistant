'use client'

import { useLocale, useTranslations } from 'next-intl'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface HistoryPoint {
  average_score: number
  recorded_at: string
}

interface ProgressTrendGraphProps {
  data: HistoryPoint[]
  topic: string
}

export function ProgressTrendGraph({ data, topic }: ProgressTrendGraphProps) {
  const locale = useLocale()
  const t = useTranslations('recovery')

  if (!data || data.length < 2) {
    return (
      <div className="flex items-center justify-center h-32 text-foreground-muted text-xs">
        {t('not_enough_data')}
      </div>
    )
  }

  const formatted = data.map(p => ({
    date: new Date(p.recorded_at).toLocaleDateString(locale, { month: 'short', day: 'numeric' }),
    score: p.average_score,
  }))

  const firstVal = formatted[0].score
  const lastVal = formatted[formatted.length - 1].score
  const trendColor = lastVal > firstVal ? '#22c55e' : lastVal < firstVal ? '#ef4444' : '#6b7280'

  return (
    <div className="w-full h-32">
      <div className="flex items-center justify-between text-xs text-foreground-muted mb-1">
        <span>{t('progress_over_time')}</span>
        <span style={{ color: trendColor }}>
          {firstVal.toFixed(0)}% → {lastVal.toFixed(0)}%
        </span>
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formatted}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: 'hsl(var(--foreground-muted))' }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--foreground-muted))' }} tickFormatter={(v: number) => `${v}%`} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <Line type="monotone" dataKey="score" stroke={trendColor} strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
