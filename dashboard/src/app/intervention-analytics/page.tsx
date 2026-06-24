'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity, BarChart3, CheckCircle, Clock,
  TrendingUp, AlertTriangle, Target, Brain,
  Award, Zap, Loader2, GitCompare,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface SummaryData {
  total_interventions: number
  completed_count: number
  active_count: number
  completion_rate: number
  average_effectiveness: number
  effectiveness_by_type: Record<string, number>
  effectiveness_by_topic: Record<string, number>
}

interface LeaderboardEntry {
  id: string
  intervention_type: string
  topic: string | null
  effectiveness_score: number | null
  completion_days: number | null
  completed_at: string | null
}

interface LearningInsights {
  effectiveness_by_type: Record<string, number>
  global_average: number
  top_recommended_type: string | null
  learned_boost: number
}

interface TrendPoint {
  period: string
  avg_effectiveness: number
  count: number
}

interface TypeComparisonMetrics {
  intervention_type: string
  count: number
  avg_effectiveness: number
  avg_mastery_change: number | null
  avg_readiness_change: number | null
  avg_retention_change: number | null
  avg_misconception_reduction: number | null
  avg_completion_days: number | null
}

interface DashboardData {
  summary: SummaryData
  leaderboard: LeaderboardEntry[]
  learning_insights: LearningInsights | null
  trends: TrendPoint[]
  comparison: { types: TypeComparisonMetrics[] } | null
  overall_confidence: number
  total_kb_entries: number
}

function StatCard({ icon: Icon, label, value, color }: {
  icon: React.ElementType
  label: string
  value: string | number
  color: string
}) {
  return (
    <div className="bg-card rounded-xl border border-border p-4">
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-9 h-9 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-4.5 h-4.5" />
        </div>
        <span className="text-2xl font-bold text-foreground">{value}</span>
      </div>
      <p className="text-xs text-foreground-muted">{label}</p>
    </div>
  )
}

export default function InterventionAnalyticsPage() {
  const router = useRouter()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchDashboard = async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await fetchWithAuth('/interventions/analytics/dashboard')
      setData(d)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchDashboard()
  }, [router])

  if (!isAuthenticated()) return null

  if (loading) {
    return (
      <DashboardLayout breadcrumbs={[
        { label: 'Overview', href: '/v2/overview' },
        { label: 'Intervention Analytics' },
      ]}>
        <div className="text-center py-24">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-foreground-muted" />
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout breadcrumbs={[
        { label: 'Overview', href: '/v2/overview' },
        { label: 'Intervention Analytics' },
      ]}>
        <div className="text-center py-16">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <p className="text-red-400">{error}</p>
        </div>
      </DashboardLayout>
    )
  }

  if (!data || data.summary.total_interventions === 0) {
    return (
      <DashboardLayout breadcrumbs={[
        { label: 'Overview', href: '/v2/overview' },
        { label: 'Intervention Analytics' },
      ]}>
        <div className="text-center py-24">
          <Activity className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">No intervention data yet</p>
          <p className="text-sm text-foreground-muted/60 mt-1">Complete interventions to see analytics</p>
        </div>
      </DashboardLayout>
    )
  }

  const { summary, leaderboard, learning_insights, trends, comparison } = data
  const sortedByType = Object.entries(summary.effectiveness_by_type)
    .sort(([, a], [, b]) => b - a)
  const sortedByTopic = Object.entries(summary.effectiveness_by_topic)
    .sort(([, a], [, b]) => b - a)

  return (
    <DashboardLayout breadcrumbs={[
      { label: 'Overview', href: '/v2/overview' },
      { label: 'Intervention Analytics' },
    ]}>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Intervention Analytics</h1>
        <p className="text-sm text-foreground-muted mt-1">
          Track effectiveness, compare strategies, and discover what works
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <StatCard icon={BarChart3} label="Total" value={summary.total_interventions} color="text-primary bg-primary/10" />
        <StatCard icon={CheckCircle} label="Completed" value={summary.completed_count} color="text-green-400 bg-green-500/10" />
        <StatCard icon={Clock} label="Active" value={summary.active_count} color="text-amber-400 bg-amber-500/10" />
        <StatCard icon={TrendingUp} label="Completion Rate" value={`${summary.completion_rate}%`} color="text-blue-400 bg-blue-500/10" />
        <StatCard icon={Award} label="Avg Effectiveness" value={`${summary.average_effectiveness.toFixed(1)}%`} color="text-purple-400 bg-purple-500/10" />
      </div>

      {/* Confidence row */}
      <div className="flex items-center gap-4 mb-6">
        <div className="bg-card rounded-xl border border-border px-4 py-3 flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-foreground-muted">Statistical Confidence</span>
            <span className="text-sm font-bold text-cyan-400">{(data.overall_confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1.5 bg-border rounded-full overflow-hidden">
            <div className="h-full rounded-full bg-cyan-400 transition-all" style={{ width: `${data.overall_confidence * 100}%` }} />
          </div>
        </div>
        <div className="bg-card rounded-xl border border-border px-4 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
            <BarChart3 className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs text-foreground-muted">KB Entries</p>
            <p className="text-sm font-bold text-foreground">{data.total_kb_entries}</p>
          </div>
        </div>
      </div>

      {/* Main grid: 2 columns */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Effectiveness by Type */}
        {sortedByType.length > 0 && (
          <div className="bg-card rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" />
              Effectiveness by Type
            </h3>
            <div className="space-y-2.5">
              {sortedByType.map(([type, score]) => (
                <div key={type}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-foreground-muted">{type.replace(/_/g, ' ')}</span>
                    <span className="font-mono text-foreground">{score.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-border rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${Math.min(score, 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Effectiveness by Topic */}
        {sortedByTopic.length > 0 && (
          <div className="bg-card rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <Brain className="w-4 h-4 text-purple-400" />
              Effectiveness by Topic
            </h3>
            <div className="space-y-2.5">
              {sortedByTopic.map(([topic, score]) => (
                <div key={topic}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-foreground-muted">{topic}</span>
                    <span className="font-mono text-foreground">{score.toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-border rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-purple-400 transition-all" style={{ width: `${Math.min(score, 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Leaderboard */}
      {leaderboard.length > 0 && (
        <div className="bg-card rounded-xl border border-border p-5 mb-6">
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Award className="w-4 h-4 text-amber-400" />
            Intervention Leaderboard
          </h3>
          <div className="overflow-hidden">
            <table className="w-full">
              <thead className="bg-background-secondary">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-foreground-muted uppercase">#</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-foreground-muted uppercase">Type</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-foreground-muted uppercase">Topic</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-foreground-muted uppercase">Effectiveness</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-foreground-muted uppercase">Completed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {leaderboard.map((entry, idx) => (
                  <tr key={entry.id} className="hover:bg-background-secondary/50">
                    <td className="px-3 py-2.5 text-sm text-foreground-muted">{idx + 1}</td>
                    <td className="px-3 py-2.5 text-sm font-medium text-foreground">{entry.intervention_type.replace(/_/g, ' ')}</td>
                    <td className="px-3 py-2.5 text-sm text-foreground-muted">{entry.topic || '—'}</td>
                    <td className="px-3 py-2.5 text-sm">
                      {entry.effectiveness_score !== null ? (
                        <span className="inline-flex items-center gap-1 text-green-400 font-medium">
                          <Zap className="w-3.5 h-3.5" />
                          {entry.effectiveness_score.toFixed(1)}%
                        </span>
                      ) : (
                        <span className="text-foreground-muted/50">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-foreground-muted">
                      {entry.completed_at ? entry.completed_at.slice(0, 10) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Strategy Comparison */}
      {comparison && comparison.types.length >= 2 && (
        <div className="bg-card rounded-xl border border-border p-5 mb-6">
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <GitCompare className="w-4 h-4 text-cyan-400" />
            Strategy Comparison
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-background-secondary">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-foreground-muted uppercase">Metric</th>
                  {comparison.types.map(t => (
                    <th key={t.intervention_type} className="px-3 py-2 text-left text-xs font-medium text-foreground-muted uppercase">
                      {t.intervention_type.replace(/_/g, ' ')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[
                  { label: 'Count', key: 'count' as const, fmt: (v: number) => String(v), color: '' },
                  { label: 'Effectiveness', key: 'avg_effectiveness' as const, fmt: (v: number) => `${v.toFixed(1)}%`, color: 'text-green-400' },
                  { label: 'Mastery Change', key: 'avg_mastery_change' as const, fmt: (v: number | null) => v !== null ? `${(v * 100).toFixed(1)}%` : '—', color: 'text-blue-400' },
                  { label: 'Readiness Change', key: 'avg_readiness_change' as const, fmt: (v: number | null) => v !== null ? `${(v * 100).toFixed(1)}%` : '—', color: 'text-violet-400' },
                  { label: 'Retention Change', key: 'avg_retention_change' as const, fmt: (v: number | null) => v !== null ? `${(v * 100).toFixed(1)}%` : '—', color: 'text-amber-400' },
                  { label: 'Misconception Reduction', key: 'avg_misconception_reduction' as const, fmt: (v: number | null) => v !== null ? `${(v * 100).toFixed(1)}%` : '—', color: 'text-rose-400' },
                  { label: 'Completion Days', key: 'avg_completion_days' as const, fmt: (v: number | null) => v !== null ? v.toFixed(1) : '—', color: 'text-cyan-400' },
                ].map(row => (
                  <tr key={row.label} className="hover:bg-background-secondary/50">
                    <td className="px-3 py-2.5 text-sm text-foreground-muted font-medium">{row.label}</td>
                    {comparison.types.map(t => {
                      const val = t[row.key] as number | null
                      return (
                        <td key={t.intervention_type} className={`px-3 py-2.5 text-sm ${row.color} ${row.color ? 'font-medium' : ''}`}>
                          {row.fmt(val as never)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Bottom grid: learning insights + trends */}
      <div className="grid grid-cols-2 gap-6">
        {/* Learning Insights */}
        {learning_insights && (
          <div className="bg-card rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <Brain className="w-4 h-4 text-violet-400" />
              What the System Learned
            </h3>
            <div className="p-3 rounded-lg bg-gradient-to-br from-violet-500/5 to-purple-500/10 border border-violet-500/10 mb-3">
              <p className="text-sm text-foreground-muted mb-1">Best Performing Type</p>
              <p className="text-lg font-bold text-violet-400">
                {learning_insights.top_recommended_type?.replace(/_/g, ' ') || 'N/A'}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-background-secondary">
                <p className="text-xs text-foreground-muted">Global Avg Effectiveness</p>
                <p className="text-lg font-bold text-foreground">{learning_insights.global_average.toFixed(1)}%</p>
              </div>
              <div className="p-3 rounded-lg bg-background-secondary">
                <p className="text-xs text-foreground-muted">Learned Boost</p>
                <p className="text-lg font-bold text-amber-400">+{(learning_insights.learned_boost * 100).toFixed(1)}%</p>
              </div>
            </div>
          </div>
        )}

        {/* Effectiveness Trends */}
        {trends.length > 0 && (
          <div className="bg-card rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-400" />
              Monthly Trends
            </h3>
            <div className="space-y-2.5">
              {trends.map((point) => (
                <div key={point.period}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-foreground-muted">{point.period.slice(0, 7)}</span>
                    <span className="font-mono text-foreground">
                      {point.avg_effectiveness.toFixed(1)}% <span className="text-foreground-muted/50">({point.count})</span>
                    </span>
                  </div>
                  <div className="h-2 bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-blue-400 transition-all"
                      style={{ width: `${Math.min(point.avg_effectiveness, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
