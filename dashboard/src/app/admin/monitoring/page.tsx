'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

interface MonitoringData {
  total_requests: number
  failed_requests: number
  fallback_rate: number
  fallbacks: number
}

export default function AdminMonitoringPage() {
  const [data, setData] = useState<MonitoringData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWithAuth('/api/admin/monitoring')
      .then(setData)
      .catch(err => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!data) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Model Monitoring</h1>
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-blue-50">
          <div className="text-2xl font-bold text-blue-700">{data.total_requests}</div>
          <div className="text-sm text-blue-600">Total Requests</div>
        </div>
        <div className="p-4 rounded-lg bg-red-50">
          <div className="text-2xl font-bold text-red-700">{data.failed_requests}</div>
          <div className="text-sm text-red-600">Failed</div>
        </div>
        <div className="p-4 rounded-lg bg-amber-50">
          <div className="text-2xl font-bold text-amber-700">{data.fallback_rate}%</div>
          <div className="text-sm text-amber-600">Fallback Rate</div>
        </div>
      </div>
      {data.fallbacks > 0 && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm">
          <strong>Fallbacks triggered:</strong> {data.fallbacks} times
        </div>
      )}
    </div>
  )
}
