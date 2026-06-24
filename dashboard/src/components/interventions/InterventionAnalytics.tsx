'use client'

import { useEffect, useState } from 'react'
import {
  Activity, BarChart3, CheckCircle, Clock,
  TrendingUp, AlertTriangle, Target,
} from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

interface AnalyticsData {
  total_interventions: number
  completed_count: number
  active_count: number
  completion_rate: number
  average_effectiveness: number
  effectiveness_by_type: Record<string, number>
  effectiveness_by_topic: Record<string, number>
}

export function InterventionAnalytics({ teacherId }: { teacherId?: string }) {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAnalytics = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = teacherId ? `?teacher_id=${teacherId}` : ''
      const d = await fetchWithAuth(`/interventions/analytics/summary${params}`)
      setData(d)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAnalytics() }, [teacherId])

  if (loading) {
    return (
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-border rounded w-1/3" />
          <div className="grid grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <div key={i} className="h-16 bg-border rounded" />)}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-card rounded-xl border border-border p-6 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-sm text-red-400">{error}</p>
      </div>
    )
  }

  if (!data || data.total_interventions === 0) {
    return (
      <div className="bg-card rounded-xl border border-border p-6 text-center">
        <Activity className="w-8 h-8 text-border mx-auto mb-2" />
        <p className="text-sm text-foreground-muted">No interventions yet</p>
      </div>
    )
  }

  const metrics = [
    { label: 'Total', value: data.total_interventions, icon: BarChart3, color: 'text-primary bg-primary/10' },
    { label: 'Completed', value: data.completed_count, icon: CheckCircle, color: 'text-green-400 bg-green-500/10' },
    { label: 'Active', value: data.active_count, icon: Clock, color: 'text-amber-400 bg-amber-500/10' },
    { label: 'Completion Rate', value: `${data.completion_rate}%`, icon: TrendingUp, color: 'text-blue-400 bg-blue-500/10' },
  ]

  const sortedByType = Object.entries(data.effectiveness_by_type)
    .sort(([, a], [, b]) => b - a)
  const sortedByTopic = Object.entries(data.effectiveness_by_topic)
    .sort(([, a], [, b]) => b - a)

  return (
    <div className="space-y-6">
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold text-foreground">Intervention Analytics</h2>
        </div>
        <div className="grid grid-cols-4 gap-4">
          {metrics.map(m => (
            <div key={m.label} className="p-3 rounded-lg bg-background-secondary">
              <div className={`w-8 h-8 rounded-lg ${m.color} flex items-center justify-center mb-2`}>
                <m.icon className="w-4 h-4" />
              </div>
              <p className="text-2xl font-bold text-foreground">{m.value}</p>
              <p className="text-xs text-foreground-muted">{m.label}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <span className="text-sm text-foreground-muted">Avg. Effectiveness:</span>
          <span className="text-lg font-bold text-primary">{data.average_effectiveness.toFixed(1)}%</span>
        </div>
      </div>

      {sortedByType.length > 0 && (
        <div className="bg-card rounded-xl border border-border p-6">
          <h3 className="text-sm font-semibold text-foreground mb-3">Effectiveness by Type</h3>
          <div className="space-y-2">
            {sortedByType.map(([type, score]) => (
              <div key={type} className="flex items-center gap-3">
                <span className="text-xs text-foreground-muted w-32 truncate">{type.replace(/_/g, ' ')}</span>
                <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${Math.min(score, 100)}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-foreground-muted w-8 text-right">{score.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sortedByTopic.length > 0 && (
        <div className="bg-card rounded-xl border border-border p-6">
          <h3 className="text-sm font-semibold text-foreground mb-3">Effectiveness by Topic</h3>
          <div className="space-y-2">
            {sortedByTopic.map(([topic, score]) => (
              <div key={topic} className="flex items-center gap-3">
                <span className="text-xs text-foreground-muted w-32 truncate">{topic}</span>
                <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-purple-400 transition-all"
                    style={{ width: `${Math.min(score, 100)}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-foreground-muted w-8 text-right">{score.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
