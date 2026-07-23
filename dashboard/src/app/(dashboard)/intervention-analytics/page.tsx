'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'
import { TrendingUp, Award, Compass, RefreshCw, AlertCircle } from 'lucide-react'
import { ResponsiveContainer, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Bar } from 'recharts'

interface LeaderboardEntry {
  id: string
  intervention_type: string
  topic: string
  effectiveness_score: number
  completed_at: string | null
}

interface TrendPoint {
  period: string
  avg_effectiveness: number
  count: number
}

interface Insights {
  effectiveness_by_type: Record<string, number>
  global_average: number
  top_recommended_type: string | null
  learned_boost: number
}

export default function InterventionAnalyticsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Data States
  const [insights, setInsights] = useState<Insights | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [trends, setTrends] = useState<TrendPoint[]>([])

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [ins, lead, trendData] = await Promise.all([
        fetchWithAuth('/api/interventions/learning-insights').then(r => r.json()),
        fetchWithAuth('/api/interventions/analytics/leaderboard?limit=10').then(r => r.json()),
        fetchWithAuth('/api/interventions/analytics/trends?months=6').then(r => r.json()),
      ])
      setInsights(ins)
      setLeaderboard(lead)
      setTrends(trendData)
    } catch (err: any) {
      setError(err.message || 'Failed to load intervention analytics')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    fetchData()
  }, [router])

  return (
    <DashboardLayout breadcrumbs={[{ label: 'Interventions', href: '/intervention-analytics' }, { label: 'Effectiveness Analytics' }]}>
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="verge-display text-4xl text-v2-text-primary leading-none">Intervention Effectiveness</h1>
            <p className="text-sm text-v2-text-secondary mt-1">
              Measure, compare, and optimize Socratic reviews, recovery tasks, and adaptive practice outcomes.
            </p>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-2.5 bg-v2-surface border border-v2-border hover:border-v2-accent rounded-xl text-v2-text-primary disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {loading && !insights ? (
          <div className="py-20 flex justify-center">
            <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" />
          </div>
        ) : (
          <>
            {/* Stats Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-v2-surface border border-v2-border p-5 rounded-[20px]">
                <p className="text-xs text-v2-text-secondary uppercase font-semibold">Global Avg Effectiveness</p>
                <p className="verge-display text-3xl text-v2-accent mt-1">
                  {insights?.global_average != null ? `${insights.global_average}%` : '—'}
                </p>
              </div>
              <div className="bg-v2-surface border border-v2-border p-5 rounded-[20px]">
                <p className="text-xs text-v2-text-secondary uppercase font-semibold">Top Performing Inoculation</p>
                <p className="text-base font-bold text-v2-text-primary mt-2.5 truncate">
                  {insights?.top_recommended_type
                    ? insights.top_recommended_type.replace(/_/g, ' ').toUpperCase()
                    : 'None Logged'}
                </p>
              </div>
              <div className="bg-v2-surface border border-v2-border p-5 rounded-[20px]">
                <p className="text-xs text-v2-text-secondary uppercase font-semibold">Recommendation Boost</p>
                <p className="verge-display text-3xl text-v2-text-primary mt-1">
                  {insights?.learned_boost != null ? `+${(insights.learned_boost * 100).toFixed(1)}%` : '0%'}
                </p>
              </div>
            </div>

            {/* Dashboard Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Trends Chart */}
              <div className="lg:col-span-2 bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4">
                <h2 className="text-lg font-bold text-v2-text-primary flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-v2-accent" /> Ingestion Trends & Gains
                </h2>
                
                {trends.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={trends}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                      <XAxis dataKey="period" tick={{ fill: '#949494', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#949494', fontSize: 10 }} domain={[0, 100]} />
                      <Tooltip contentStyle={{ backgroundColor: '#2d2d2d', borderColor: 'rgba(255,255,255,0.2)' }} />
                      <Bar dataKey="avg_effectiveness" fill="#3cffd0" name="Avg Effectiveness" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="py-20 text-center text-sm text-v2-text-secondary">
                    No historical trend data found. Apply and complete interventions to generate logs.
                  </div>
                )}
              </div>

              {/* Effectiveness by Type */}
              <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4">
                <h2 className="text-lg font-bold text-v2-text-primary flex items-center gap-2">
                  <Compass className="w-5 h-5 text-v2-accent" /> Strategy Comparison
                </h2>

                {insights?.effectiveness_by_type && Object.keys(insights.effectiveness_by_type).length > 0 ? (
                  <div className="flex flex-col gap-3">
                    {Object.entries(insights.effectiveness_by_type).map(([type, score]) => (
                      <div key={type} className="flex flex-col gap-1.5 p-3 rounded-xl border border-v2-border bg-v2-bg/40">
                        <div className="flex justify-between items-center text-xs font-semibold">
                          <span className="text-v2-text-primary uppercase tracking-wider">
                            {type.replace(/_/g, ' ')}
                          </span>
                          <span className="text-v2-accent font-bold">{score}%</span>
                        </div>
                        <div className="w-full h-1.5 bg-v2-bg rounded-full overflow-hidden">
                          <div
                            className="h-full bg-v2-accent"
                            style={{ width: `${score}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-12 text-center text-xs text-v2-text-secondary">
                    No comparative strategy logs available.
                  </div>
                )}
              </div>
            </div>

            {/* Leaderboard Table */}
            <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4">
              <h2 className="text-lg font-bold text-v2-text-primary flex items-center gap-2 border-b border-v2-border/40 pb-2.5">
                <Award className="w-5 h-5 text-v2-accent" /> Completed Intervention Leaderboard
              </h2>

              {leaderboard.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-v2-border/30 text-xs text-v2-text-secondary uppercase">
                        <th className="py-2.5 font-semibold">Type</th>
                        <th className="py-2.5 font-semibold">Topic</th>
                        <th className="py-2.5 font-semibold">Date Completed</th>
                        <th className="py-2.5 font-semibold text-right">Effectiveness Score</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-v2-border/20">
                      {leaderboard.map(entry => (
                        <tr key={entry.id} className="text-sm hover:bg-v2-bg/30">
                          <td className="py-3 font-semibold text-v2-text-primary uppercase tracking-wider text-xs">
                            {entry.intervention_type.replace(/_/g, ' ')}
                          </td>
                          <td className="py-3 text-v2-text-secondary font-medium">
                            {entry.topic}
                          </td>
                          <td className="py-3 text-xs text-v2-text-secondary">
                            {entry.completed_at ? new Date(entry.completed_at).toLocaleDateString() : '—'}
                          </td>
                          <td className="py-3 text-right">
                            <span className="text-sm font-bold text-v2-accent">
                              {entry.effectiveness_score}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-12 text-center text-sm text-v2-text-secondary">
                  No completed interventions mapped to date.
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  )
}
