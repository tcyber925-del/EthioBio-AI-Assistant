'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { BarChart3, AlertTriangle, RefreshCw } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend } from 'recharts'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface MonitoringData {
  total_requests: number; failed_requests: number
  fallback_rate: number; fallbacks: number
}

export default function MonitoringPage() {
  const router = useRouter()
  const tm = useTranslations('monitoring')
  const tc = useTranslations('common')
  const [data, setData] = useState<MonitoringData | null>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [providers, setProviders] = useState<any[]>([])
  const [activeModel, setActiveModel] = useState('')

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [mon, dash, prov, active] = await Promise.all([
        fetchWithAuth('/api/admin/monitoring').then(r => r.json()),
        fetchWithAuth('/api/admin/dashboard').then(r => r.json()),
        fetchWithAuth('/models/providers').then(r => r.json()),
        fetchWithAuth('/models/active').then(r => r.json()),
      ])
      setData(mon)
      setLogs(dash.recent_logs || [])
      setProviders(prov)
      setActiveModel(active.model)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchData()
  }, [router])

  if (loading) return <div className="grid grid-cols-1 md:grid-cols-3 gap-5">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  if (error) return (
    <div className="text-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-red-400">{error}</p>
      <button onClick={fetchData} className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
        <RefreshCw className="w-4 h-4 inline mr-1" /> {tc('retry')}
      </button>
    </div>
  )

  const pieData = [
    { name: tm('success'), value: logs.filter(l => l.success).length },
    { name: tm('failed'), value: logs.filter(l => !l.success).length },
  ]
  const COLORS = ['#22c55e', '#ef4444']

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{tm('title')}</h1>
          <p className="text-sm text-foreground-muted mt-1">{tm('subtitle')}</p>
        </div>
        <button onClick={fetchData} className="flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-lg hover:bg-card transition-colors text-foreground-muted hover:text-foreground">
          <RefreshCw className="w-4 h-4" /> {tc('refresh')}
        </button>
      </div>

      <div className="bg-card rounded-xl border border-border p-5 mb-6">
        <h2 className="text-lg font-semibold text-foreground mb-4">{tm('provider_status')}</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {providers.map(p => (
            <div key={p.name} className={`p-4 rounded-lg border ${p.is_healthy ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm">{p.name}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs ${p.is_healthy ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {p.is_healthy ? tm('online') : tm('offline')}
                </span>
              </div>
              <p className="text-xs text-foreground-muted mt-1">{p.provider_type}</p>
              <p className="text-xs text-foreground-muted mt-1">{p.available_models.length} model(s)</p>
            </div>
          ))}
        </div>
        <div className="mt-3 text-sm text-foreground-muted">
          {tm('active_model')} <span className="font-mono text-foreground">{activeModel}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
        <div className="bg-card rounded-xl border border-border p-5">
          <p className="text-sm text-foreground-muted">{tm('total_requests')}</p>
          <p className="text-2xl font-bold text-foreground">{data?.total_requests ?? 0}</p>
        </div>
        <div className="bg-card rounded-xl border border-border p-5">
          <p className="text-sm text-foreground-muted">{tm('failed')}</p>
          <p className="text-2xl font-bold text-red-400">{data?.failed_requests ?? 0}</p>
        </div>
        <div className="bg-card rounded-xl border border-border p-5">
          <p className="text-sm text-foreground-muted">{tm('fallback_rate')}</p>
          <p className="text-2xl font-bold text-orange-400">{data?.fallback_rate ?? 0}%</p>
        </div>
        <div className="bg-card rounded-xl border border-border p-5">
          <p className="text-sm text-foreground-muted">{tm('fallbacks_used')}</p>
          <p className="text-2xl font-bold text-foreground">{data?.fallbacks ?? 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-card rounded-xl border border-border p-5">
          <h2 className="text-lg font-semibold text-foreground mb-4">{tm('request_success_rate')}</h2>
          {logs.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                </Pie>
                <Legend wrapperStyle={{ color: '#f1f5f9' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-foreground-muted text-sm py-12 text-center">{tc('no_data_yet')}</p>
          )}
        </div>
        <div className="bg-card rounded-xl border border-border p-5">
          <h2 className="text-lg font-semibold text-foreground mb-4">{tm('model_usage')}</h2>
          {logs.length > 0 ? (
            <div className="space-y-2 max-h-[250px] overflow-y-auto">
              {Object.entries(
                logs.reduce((acc: Record<string, number>, l) => {
                  const m = l.model_used || 'unknown'
                  acc[m] = (acc[m] || 0) + 1
                  return acc
                }, {})
              ).map(([model, count]) => (
                <div key={model} className="flex items-center justify-between p-2 hover:bg-background-secondary rounded">
                  <span className="text-sm font-mono text-foreground-muted">{model}</span>
                  <span className="text-sm font-semibold text-foreground">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-foreground-muted text-sm py-12 text-center">{tc('no_data_yet')}</p>
          )}
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border">
        <div className="px-5 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">{tm('request_logs')}</h2>
        </div>
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full">
            <thead className="bg-background-secondary">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tm('type')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tc('model_label')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tm('status')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tm('latency')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tm('time')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {logs.map((log: any, i: number) => (
                <tr key={log.id || i} className="hover:bg-background-secondary/50">
                  <td className="px-5 py-3 text-sm text-foreground">{log.request_type}</td>
                  <td className="px-5 py-3 text-sm text-foreground-muted font-mono text-xs">{log.model_used}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      log.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                    }`}>{log.success ? tm('success') : tm('failed')}</span>
                  </td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{log.latency_ms}ms</td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{log.created_at?.slice(11, 19) || '-'}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-12 text-center text-foreground-muted">{tc('no_logs_yet')}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
