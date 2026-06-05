'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

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
      .then(setData)
      .catch(err => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  if (error) return <p className="text-red-600">{tc('error')}: {error}</p>
  if (!data) return <p className="text-gray-500">{tc('loading')}</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{tm('title')}</h1>
      <p className="text-sm text-foreground-muted mb-4">{tm('monitoring_subtitle')}</p>
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-blue-50">
          <div className="text-2xl font-bold text-blue-700">{data.total_requests}</div>
          <div className="text-sm text-blue-600">{tm('total_requests')}</div>
        </div>
        <div className="p-4 rounded-lg bg-red-50">
          <div className="text-2xl font-bold text-red-700">{data.failed_requests}</div>
          <div className="text-sm text-red-600">{tm('failed_label')}</div>
        </div>
        <div className="p-4 rounded-lg bg-amber-50">
          <div className="text-2xl font-bold text-amber-700">{data.fallback_rate}%</div>
          <div className="text-sm text-amber-600">{tm('fallback_rate')}</div>
        </div>
      </div>
      {data.fallbacks > 0 && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
          <strong>{tm('fallbacks_triggered')}</strong> {tm('times', { count: data.fallbacks })}
        </div>
      )}
    </div>
  )
}
