'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'

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
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWithAuth('/api/admin/monitoring')
      .then(res => res.json())
      .then(setData)
      .catch(err => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  if (error) return <p className="text-red-400">{tc('error')}: {error}</p>
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
