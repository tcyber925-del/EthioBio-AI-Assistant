'use client'

import { useTranslations } from 'next-intl'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

interface RadarDataPoint {
  topic: string
  mastery: number
}

interface MasteryRadarChartProps {
  data: RadarDataPoint[]
}

export function MasteryRadarChart({ data }: MasteryRadarChartProps) {
  const t = useTranslations('recovery')

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-foreground-muted text-sm">
        {t('no_topic_data')}
      </div>
    )
  }

  const maxMastery = Math.max(...data.map(d => d.mastery), 60)
  const niceMax = Math.ceil(maxMastery / 10) * 10

  return (
    <div className="w-full h-72">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
          <PolarGrid stroke="hsl(var(--border))" />
          <PolarAngleAxis
            dataKey="topic"
            tick={{ fill: 'hsl(var(--foreground-muted))', fontSize: 11 }}
            tickFormatter={(v: string) => v.length > 12 ? v.slice(0, 12) + '…' : v}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, niceMax]}
            tick={{ fill: 'hsl(var(--foreground-muted))', fontSize: 10 }}
            tickFormatter={(v: number) => `${v}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
              fontSize: '13px',
            }}
            formatter={(value: number) => [`${value.toFixed(0)}%`, t('mastery_label')]}
          />
          <Radar
            name={t('mastery_label')}
            dataKey="mastery"
            stroke="hsl(var(--primary))"
            fill="hsl(var(--primary))"
            fillOpacity={0.2}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
