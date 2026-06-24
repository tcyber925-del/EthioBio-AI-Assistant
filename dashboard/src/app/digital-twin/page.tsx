'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity, Brain, Clock, Target, AlertTriangle,
  Shield, RefreshCw, Loader2, TrendingUp,
  TrendingDown, Minus, ChevronDown, ChevronRight,
  FlaskConical, Plus, X,
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

interface ForecastData {
  generated_at: string
  mastery: {
    topic: string
    current: number
    projected: number
    trend: string
    confidence: string
    data_points: number
  }[]
  retention: {
    topic: string
    current: number
    projected: number
    retention_rate: string
    confidence: string
  }[]
  readiness: {
    overall: { current: number; projected: number }
    topic: { topic: string; current: number; projected: number }[]
  }
  risk: {
    topic: string
    type: string
    severity: string
    current: number
    projected: number
    detail: string
  }[]
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

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'improving') return <TrendingUp className="w-3.5 h-3.5 text-green-400" />
  if (trend === 'declining') return <TrendingDown className="w-3.5 h-3.5 text-red-400" />
  return <Minus className="w-3.5 h-3.5 text-foreground-muted" />
}

export default function DigitalTwinPage() {
  const router = useRouter()
  const userId = getUserId()
  const [data, setData] = useState<DashboardData | null>(null)
  const [forecast, setForecast] = useState<ForecastData | null>(null)
  const [loading, setLoading] = useState(true)
  const [forecastOpen, setForecastOpen] = useState(false)
  const [rebuilding, setRebuilding] = useState(false)
  const [simOpen, setSimOpen] = useState(false)
  const [simActions, setSimActions] = useState<{ type: string; topic: string; value: number }[]>([])
  const [simResult, setSimResult] = useState<{ baseline: any; simulated: any } | null>(null)
  const [simRunning, setSimRunning] = useState(false)

  const fetchTwin = async () => {
    if (!userId) return
    setLoading(true)
    try {
      const [twin, fc] = await Promise.all([
        fetchWithAuth(`/digital-twin/${userId}/dashboard`),
        fetchWithAuth(`/digital-twin/${userId}/forecast`).catch(() => null),
      ])
      setData(twin)
      setForecast(fc)
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

  const runSimulation = useCallback(async () => {
    if (!userId || simActions.length === 0) return
    setSimRunning(true)
    try {
      const result = await fetchWithAuth(`/digital-twin/${userId}/simulate?weeks_ahead=4`, {
        method: 'POST',
        body: JSON.stringify(simActions),
      })
      setSimResult(result)
    } catch {
      setSimResult(null)
    } finally {
      setSimRunning(false)
    }
  }, [userId, simActions])

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

            {forecast && (
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <button
                  onClick={() => setForecastOpen(!forecastOpen)}
                  className="w-full flex items-center justify-between p-4 hover:bg-background-secondary transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-foreground-muted" />
                    <h2 className="text-sm font-semibold text-foreground">
                      Forecast ({forecast.mastery.length} topics · {forecast.generated_at ? new Date(forecast.generated_at).toLocaleDateString() : ''})
                    </h2>
                  </div>
                  {forecastOpen ? <ChevronDown className="w-4 h-4 text-foreground-muted" /> : <ChevronRight className="w-4 h-4 text-foreground-muted" />}
                </button>
                {forecastOpen && (
                  <div className="px-4 pb-4 space-y-4">
                    {forecast.mastery.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-foreground-muted mb-2 uppercase tracking-wider">Mastery Trend</p>
                        <div className="space-y-1">
                          {forecast.mastery.map((m) => (
                            <div key={m.topic} className="flex items-center gap-3 p-2 rounded-lg bg-background-secondary">
                              <TrendIcon trend={m.trend} />
                              <span className="text-sm text-foreground flex-1">{m.topic}</span>
                              <span className="text-xs text-foreground-muted">
                                {Math.round(m.current * 100)}% → {Math.round(m.projected * 100)}%
                              </span>
                              <span className={`text-xs px-1.5 py-0.5 rounded ${
                                m.confidence === 'high' ? 'bg-green-500/10 text-green-400' :
                                m.confidence === 'medium' ? 'bg-yellow-500/10 text-yellow-400' :
                                'bg-foreground-muted/10 text-foreground-muted'
                              }`}>{m.confidence}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {forecast.readiness.overall && (
                      <div>
                        <p className="text-xs font-medium text-foreground-muted mb-2 uppercase tracking-wider">Readiness</p>
                        <div className="flex items-center gap-3 p-3 rounded-lg bg-background-secondary">
                          <Target className="w-4 h-4 text-foreground-muted" />
                          <span className="text-sm text-foreground">Overall</span>
                          <span className="text-xs text-foreground-muted">
                            {Math.round(forecast.readiness.overall.current * 100)}% → {Math.round(forecast.readiness.overall.projected * 100)}%
                          </span>
                        </div>
                      </div>
                    )}

                    {forecast.risk.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-foreground-muted mb-2 uppercase tracking-wider">Projected Risks</p>
                        <div className="space-y-1">
                          {forecast.risk.map((r, i) => (
                            <div key={i} className="flex items-start gap-3 p-2 rounded-lg bg-background-secondary">
                              <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                                r.severity === 'high' ? 'bg-red-400' : 'bg-yellow-400'
                              }`} />
                              <div>
                                <p className="text-sm font-medium text-foreground capitalize">
                                  {r.type.replace(/_/g, ' ')} · {r.topic}
                                </p>
                                <p className="text-xs text-foreground-muted">{r.detail}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {forecast.retention.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-foreground-muted mb-2 uppercase tracking-wider">Retention</p>
                        <div className="space-y-1">
                          {forecast.retention.map((r) => (
                            <div key={r.topic} className="flex items-center gap-3 p-2 rounded-lg bg-background-secondary">
                              <TrendIcon trend={r.retention_rate} />
                              <span className="text-sm text-foreground flex-1">{r.topic}</span>
                              <span className="text-xs text-foreground-muted">
                                {Math.round(r.current * 100)}% → {Math.round(r.projected * 100)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {forecast && forecast.mastery.length > 0 && (
              <div className="bg-card border border-border rounded-xl overflow-hidden">
                <button
                  onClick={() => setSimOpen(!simOpen)}
                  className="w-full flex items-center justify-between p-4 hover:bg-background-secondary transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <FlaskConical className="w-4 h-4 text-foreground-muted" />
                    <h2 className="text-sm font-semibold text-foreground">What If? — Simulate Interventions</h2>
                  </div>
                  {simOpen ? <ChevronDown className="w-4 h-4 text-foreground-muted" /> : <ChevronRight className="w-4 h-4 text-foreground-muted" />}
                </button>
                {simOpen && (
                  <div className="px-4 pb-4 space-y-3">
                    <p className="text-xs text-foreground-muted">Test how interventions would change projected outcomes</p>
                    <div className="space-y-2">
                      {simActions.map((a, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <select
                            value={a.type}
                            onChange={(e) => {
                              const next = [...simActions]
                              next[i] = { ...next[i], type: e.target.value }
                              setSimActions(next)
                            }}
                            className="text-xs bg-background-secondary border border-border rounded px-2 py-1 text-foreground"
                          >
                            <option value="boost_mastery">Boost Mastery</option>
                            <option value="add_reviews">Add Reviews</option>
                            <option value="resolve_misconception">Resolve Misconception</option>
                          </select>
                          <select
                            value={a.topic}
                            onChange={(e) => {
                              const next = [...simActions]
                              next[i] = { ...next[i], topic: e.target.value }
                              setSimActions(next)
                            }}
                            className="text-xs bg-background-secondary border border-border rounded px-2 py-1 text-foreground flex-1"
                          >
                            {forecast.mastery.map((m) => (
                              <option key={m.topic} value={m.topic}>{m.topic}</option>
                            ))}
                          </select>
                          {a.type !== 'resolve_misconception' && (
                            <input
                              type="number"
                              min={0.05}
                              max={0.5}
                              step={0.05}
                              value={a.value}
                              onChange={(e) => {
                                const next = [...simActions]
                                next[i] = { ...next[i], value: parseFloat(e.target.value) || 0 }
                                setSimActions(next)
                              }}
                              className="w-16 text-xs bg-background-secondary border border-border rounded px-2 py-1 text-foreground text-center"
                            />
                          )}
                          <button
                            onClick={() => setSimActions(simActions.filter((_, j) => j !== i))}
                            className="p-1 hover:bg-background-secondary rounded"
                          >
                            <X className="w-3.5 h-3.5 text-foreground-muted" />
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSimActions([...simActions, { type: 'boost_mastery', topic: forecast.mastery[0].topic, value: 0.1 }])}
                        className="flex items-center gap-1 text-xs text-foreground-muted hover:text-foreground px-2 py-1 rounded border border-border"
                      >
                        <Plus className="w-3 h-3" /> Add Action
                      </button>
                      {simActions.length > 0 && (
                        <button
                          onClick={runSimulation}
                          disabled={simRunning}
                          className="flex items-center gap-1 text-xs px-3 py-1 bg-primary text-white rounded hover:bg-primary-hover disabled:opacity-50"
                        >
                          {simRunning ? <Loader2 className="w-3 h-3 animate-spin" /> : <FlaskConical className="w-3 h-3" />}
                          Run
                        </button>
                      )}
                      {simResult && (
                        <button
                          onClick={() => setSimResult(null)}
                          className="text-xs text-foreground-muted hover:text-foreground px-2 py-1"
                        >
                          Clear
                        </button>
                      )}
                    </div>
                    {simResult && simResult.simulated && (
                      <div className="space-y-2 pt-2 border-t border-border">
                        <p className="text-xs font-medium text-foreground-muted">Baseline vs Simulated</p>
                        {simResult.simulated.mastery.map((sm: any) => {
                          const bm = simResult.baseline.mastery.find((bm: any) => bm.topic === sm.topic)
                          if (!bm) return null
                          return (
                            <div key={sm.topic} className="flex items-center gap-3 p-2 rounded-lg bg-background-secondary">
                              <span className="text-sm text-foreground flex-1">{sm.topic}</span>
                              <span className="text-xs text-foreground-muted">
                                {Math.round(bm.projected * 100)}% → <span className="text-green-400 font-medium">{Math.round(sm.projected * 100)}%</span>
                              </span>
                            </div>
                          )
                        })}
                        {simResult.simulated.risk.length === 0 && simResult.baseline.risk.length > 0 && (
                          <div className="flex items-center gap-2 p-2 rounded-lg bg-green-500/10 text-green-400 text-xs">
                            <TrendingUp className="w-3 h-3" />
                            All projected risks resolved
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  )
}
