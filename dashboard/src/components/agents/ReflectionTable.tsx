'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { TableSkeleton } from '@/components/Skeleton'
import { ErrorBanner } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

export interface ReflectionInfo {
  agent: string
  task: string
  verdict: string
  confidence: number
  duration_ms: number
  error: string | null
  timestamp: string | null
}

type TFn = (key: string, values?: Record<string, string | number>) => string

function timeAgo(ts: string | null, tc: TFn): string {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return tc('just_now')
  if (mins < 60) return tc('minutes_ago', { m: mins })
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return tc('hours_ago', { h: hrs })
  return tc('days_ago', { d: Math.floor(hrs / 24) })
}

const verdictBadge: Record<string, 'green' | 'red' | 'yellow'> = {
  success: 'green',
  failure: 'red',
  partial: 'yellow',
}

export default function ReflectionTable({ refreshKey }: { refreshKey: number }) {
  const t = useTranslations('agents')
  const tc = useTranslations('common')
  const [reflections, setReflections] = useState<ReflectionInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)

  const requestIdRef = useRef(0)

  const fetchReflections = useCallback(async () => {
    const requestId = ++requestIdRef.current
    setLoading(true)
    setError(null)
    try {
      const response = await fetchWithAuth('/agents/reflections?limit=20')
      if (requestId === requestIdRef.current) {
        const data = await response.json()
        setReflections(data as ReflectionInfo[])
      }
    } catch (err: unknown) {
      if (requestId === requestIdRef.current) {
        setError(normalizeException(err))
      }
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => { fetchReflections() }, [refreshKey, fetchReflections])

  if (loading) return <TableSkeleton rows={5} />
  if (error) return <ErrorBanner error={error} onAction={fetchReflections} />

  return (
    <Card className="mt-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-heading text-foreground">{t('recent_executions')}</h2>
        <Button variant="ghost" onClick={fetchReflections}>{tc('refresh')}</Button>
      </div>
      {reflections.length === 0 ? (
        <p className="text-body text-foreground-muted text-center py-8">
          {t('no_executions')}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-body">
            <thead>
              <tr className="border-b border-border text-small text-foreground-muted">
                <th className="text-left py-2 pr-4">{t('col_agent')}</th>
                <th className="text-left py-2 pr-4">{t('col_task')}</th>
                <th className="text-left py-2 pr-4">{t('col_verdict')}</th>
                <th className="text-right py-2 pr-4">{t('col_confidence')}</th>
                <th className="text-right py-2 pr-4">{t('col_duration')}</th>
                <th className="text-right py-2">{t('col_time')}</th>
              </tr>
            </thead>
            <tbody>
              {reflections.map((r, i) => (
                <tr key={i} className="border-b border-border/50 text-foreground">
                  <td className="py-2 pr-4 font-medium">{r.agent}</td>
                  <td className="py-2 pr-4 max-w-xs truncate text-foreground-muted" title={r.task}>
                    {r.task}
                  </td>
                  <td className="py-2 pr-4">
                    <Badge variant={verdictBadge[r.verdict] || 'yellow'}>
                      {['success', 'failure', 'partial'].includes(r.verdict) ? t(`verdict_${r.verdict}` as 'verdict_success') : r.verdict}
                    </Badge>
                  </td>
                  <td className="py-2 pr-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <div className="w-12 h-1.5 bg-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${Math.round(r.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs">{Math.round(r.confidence * 100)}%</span>
                    </div>
                  </td>
                  <td className="py-2 pr-4 text-right text-foreground-muted">{r.duration_ms}ms</td>
                  <td className="py-2 text-right text-foreground-muted text-small">{timeAgo(r.timestamp, tc)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
