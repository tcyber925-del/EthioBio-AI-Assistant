'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity, Brain, Clock, Target, AlertTriangle,
  Shield, RefreshCw, Loader2, TrendingUp,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId, isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface DimensionSummary {
  score?: number
  active?: number
  resolved?: number
  completed?: number
}

interface RiskIndicator {
  topic: string
  type: string
  severity: string
  detail: string
}

interface DashboardData {
  user_id: string
  overall_health: string
  dimension_summary: Record<string, DimensionSummary>
  risk_indicators: RiskIndicator[]
  last_built_at: string | null
}

const DIMENSION_ICONS: Record<string, typeof Activity> = {
  knowledge: Activity,
  mastery: TrendingUp,
  misconceptions: Brain,
  retention: Clock,
  readiness: Target,
  interventions: Shield,
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: 'bg-green-500/10 text-green-400 border-green-500/20',
  needs_attention: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  at_risk: 'bg-red-500/10 text-red-400 border-red-500/20',
}

export default function DigitalTwinPage() {
  const router = useRouter()
  const userId = getUserId()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [rebuilding, setRebuilding] = useState(false)

  const fetchTwin = async () => {
    if (!userId) return
    setLoading(true)
    try {
      const result = await fetchWithAuth(`/digital-twin/${userId}/dashboard`)
      setData(result)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  const triggerRebuild = async () => {
    if (!userId) return
    setRebuilding(true)
    try {
      await fetchWithAuth(`/digital-twin/${userId}/rebuild`, { method: 'POST' }, 60000)
      await fetchTwin()
    } catch {
      // ignore
    } finally {
      setRebuilding(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchTwin()
  }, [userId, router])

  if (!isAuthenticated()) return null

  const healthColor = data ? HEALTH_COLORS[data.overall_health] || HEALTH_COLORS.needs_attention : ''

  return (
    <DashboardLayout breadcrumbs={[
      { label: 'Overview', href: '/v2/overview' },
      { label: 'Digital Twin' },
    ]}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Digital Twin</h1>
            <p className="text-sm text-foreground-muted mt-1">
              Your virtual learner model — knowledge, mastery, misconceptions, retention, readiness, and interventions
            </p>
          </div>
          <button
            onClick={triggerRebuild}
            disabled={rebuilding}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${rebuilding ? 'animate-spin' : ''}`} />
            {rebuilding ? 'Rebuilding...' : 'Rebuild'}
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-foreground-muted" />
          </div>
        ) : !data ? (
          <div className="text-center py-16 bg-card rounded-xl border border-border">
            <Activity className="w-12 h-12 text-border mx-auto mb-3" />
            <p className="text-foreground-muted font-medium">No digital twin data yet</p>
            <p className="text-sm text-foreground-muted/60 mt-1">
              Complete assessments and activities to build your twin
            </p>
          </div>
        ) : (
          <>
            <div className={`rounded-xl border p-4 ${healthColor}`}>
              <div className="flex items-center gap-3">
                <Shield className="w-6 h-6" />
                <div>
                  <p className="text-sm font-medium capitalize">
                    {data.overall_health.replace(/_/g, ' ')}
                  </p>
                  <p className="text-xs opacity-70">
                    Last updated: {data.last_built_at ? new Date(data.last_built_at).toLocaleString() : 'Never'}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(data.dimension_summary).map(([name, summary]) => {
                const Icon = DIMENSION_ICONS[name] || Activity
                return (
                  <div key={name} className="bg-card border border-border rounded-xl p-4">
                    <div className="flex items-center gap-2 text-foreground-muted text-xs mb-3">
                      <Icon className="w-4 h-4" />
                      <span className="font-medium capitalize">{name}</span>
                    </div>
                    {'score' in summary && summary.score !== undefined ? (
                      <div className="flex items-baseline gap-1">
                        <span className="text-2xl font-bold text-foreground">
                          {Math.round(summary.score * 100)}%
                        </span>
                        <span className="text-xs text-foreground-muted">score</span>
                      </div>
                    ) : null}
                    {'active' in summary ? (
                      <div className="text-sm text-foreground">
                        <span className="font-medium">{summary.active}</span>
                        {' '}active{' '}
                        {summary.resolved !== undefined ? (
                          <span className="text-foreground-muted">
                            · {summary.resolved} resolved
                          </span>
                        ) : null}
                        {summary.completed !== undefined ? (
                          <span className="text-foreground-muted">
                            · {summary.completed} completed
                          </span>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                )
              })}
            </div>

            {data.risk_indicators.length > 0 && (
              <div className="bg-card border border-border rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <h2 className="text-sm font-semibold text-foreground">Risk Indicators</h2>
                </div>
                <div className="space-y-2">
                  {data.risk_indicators.map((r, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-background-secondary rounded-lg">
                      <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        r.severity === 'high' ? 'bg-red-400' : 'bg-yellow-400'
                      }`} />
                      <div>
                        <p className="text-sm font-medium text-foreground capitalize">
                          {r.type} · {r.topic}
                        </p>
                        <p className="text-xs text-foreground-muted">{r.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  )
}
