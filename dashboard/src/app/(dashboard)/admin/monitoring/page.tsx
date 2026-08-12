'use client'

import { useCallback, useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'
import { ErrorState } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

export const dynamic = 'force-dynamic'

interface MonitoringData {
  total_requests: number
  failed_requests: number
  fallback_rate: number
  fallbacks: number
}

export default function AdminMonitoringPage() {
  const tm = useTranslations('admin.monitoring')
  const tc = useTranslations('common')
  const [data, setData] = useState<MonitoringData | null>(null)
  const [error, setError] = useState<AppError | null>(null)

  const load = useCallback(async () => {
    try {
      const response = await fetchWithAuth('/api/admin/monitoring')
      setData(await response.json())
    } catch (err) {
      setError(normalizeException(err))
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (error) return <ErrorState error={error} onRetry={() => void load()} />
  if (!data) return <p className="text-foreground-muted text-body">{tc('loading')}</p>

  return (
    <div>
      <h1 className="text-heading text-foreground mb-2">{tm('title')}</h1>
      <p className="text-small text-foreground-muted mb-6">{tm('monitoring_subtitle')}</p>
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <p className="text-display text-blue-400">{data.total_requests}</p>
          <p className="text-small text-foreground-muted">{tm('total_requests')}</p>
        </Card>
        <Card>
          <p className="text-display text-red-400">{data.failed_requests}</p>
          <p className="text-small text-foreground-muted">{tm('failed_label')}</p>
        </Card>
        <Card>
          <p className="text-display text-yellow-400">{data.fallback_rate}%</p>
          <p className="text-small text-foreground-muted">{tm('fallback_rate')}</p>
        </Card>
      </div>
      {data.fallbacks > 0 && (
        <Card className="mt-4 border-yellow-500/20 bg-yellow-500/5">
          <p className="text-body text-yellow-400">
            <strong>{tm('fallbacks_triggered')}</strong> {tm('times', { count: data.fallbacks })}
          </p>
        </Card>
      )}
    </div>
  )
}
