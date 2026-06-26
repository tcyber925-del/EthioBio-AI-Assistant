'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw, ChevronDown } from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { HeroSection, InsightCard, MetricStrip, AIInsightPanel, LearningProgress } from '@/components/dashboard-v2'

interface ChildSummary {
  student_id: string; name: string; grade_level: number | null
  last_active: string | null; overall_readiness: number
}
interface ChildProgress {
  student_id: string; overall_readiness: number
  mastery_heatmap: Record<string, number>
  recent_quizzes: { quiz_id: string | null; score: number; total: number; created_at: string }[]
  streak: number; total_xp: number
}
interface WeeklySummary {
  summary_text: string; summary_amharic: string | null
  week_start: string; week_end: string
  is_low_performance_warning: boolean
}

function deriveParentInsights(progress: ChildProgress, summary: WeeklySummary | null): string[] {
  const insights: string[] = []
  const topics = Object.entries(progress.mastery_heatmap)
  const weak = topics.filter(([, s]) => s < 50)
  const strong = topics.filter(([, s]) => s >= 80)
  if (weak.length > 0) insights.push(`${weak.length} area${weak.length > 1 ? 's' : ''} need${weak.length === 1 ? 's' : ''} attention: ${weak.map(([t]) => t).join(', ')}.`)
  if (strong.length > 0) insights.push(`${strong.length} strength${strong.length > 1 ? 's' : ''}: ${strong.map(([t]) => t).join(', ')}. Keep up the good work!`)
  if (summary?.is_low_performance_warning) insights.push(`⚠️ Low performance warning for this period. Consider scheduling additional support.`)
  if (progress.streak >= 3) insights.push(`${progress.streak}-day streak! Consistency is building.`)
  return insights
}

export function ParentDashboard() {
  const [children, setChildren] = useState<ChildSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [progress, setProgress] = useState<ChildProgress | null>(null)
  const [summary, setSummary] = useState<WeeklySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [progressLoading, setProgressLoading] = useState(false)

  const fetchChildren = async () => {
    setLoading(true); setError(null)
    try {
      const d = await fetchWithAuth('/api/parent/children')
      setChildren(d.children || [])
      if (d.children?.length > 0) {
        setSelectedId(d.children[0].student_id)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally { setLoading(false) }
  }

  const fetchProgress = async (studentId: string) => {
    setProgressLoading(true)
    setProgress(null)
    setSummary(null)
    try {
      const [p, s] = await Promise.allSettled([
        fetchWithAuth(`/api/parent/children/${studentId}/progress`),
        fetchWithAuth(`/api/parent/children/${studentId}/weekly-summary`),
      ])
      if (p.status === 'fulfilled') setProgress(p.value)
      if (s.status === 'fulfilled') setSummary(s.value)
    } finally { setProgressLoading(false) }
  }

  useEffect(() => { fetchChildren() }, [])
  useEffect(() => { if (selectedId) fetchProgress(selectedId) }, [selectedId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin mx-auto" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-10 h-10 text-v2-error mx-auto mb-3" />
          <p className="text-sm font-medium text-v2-text-secondary mb-4">{error}</p>
          <button onClick={fetchChildren} className="inline-flex items-center gap-2 px-4 h-9 rounded-xl bg-v2-accent text-v2-inverted text-sm font-medium hover:bg-white transition-colors">
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    )
  }

  const child = children.find(c => c.student_id === selectedId)

  return (
    <>
      <HeroSection
        title="Your Child's Learning Journey"
        subtitle={child ? `${child.name} · Grade ${child.grade_level || 'N/A'}` : 'Select a child to view progress'}
        secondary={child && progress ? `XP: ${progress.total_xp} · Streak: ${progress.streak} days` : undefined}
      />

      {children.length > 1 && (
        <div className="mb-6 relative">
          <select
            value={selectedId || ''}
            onChange={e => setSelectedId(e.target.value)}
            className="appearance-none bg-v2-surface border border-v2-border rounded-xl px-4 pr-10 h-10 text-sm text-v2-text-primary outline-none focus:border-v2-accent transition-colors"
          >
            {children.map(c => (
              <option key={c.student_id} value={c.student_id}>{c.name}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-v2-text-secondary pointer-events-none" />
        </div>
      )}

      {children.length === 0 ? (
        <div className="bg-v2-surface rounded-[20px] border border-v2-border p-12 text-center">
          <p className="text-sm text-v2-text-secondary">No linked children found.</p>
        </div>
      ) : progressLoading ? (
        <div className="flex items-center justify-center h-48">
          <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin mx-auto" />
        </div>
      ) : progress ? (
        <>
          <div className="mb-6">
            <MetricStrip metrics={[
              { label: 'Readiness', value: `${progress.overall_readiness.toFixed(0)}%`, accent: true },
              { label: 'Total XP', value: progress.total_xp.toLocaleString() },
              { label: 'Streak', value: `${progress.streak} days` },
              { label: 'Topics', value: Object.keys(progress.mastery_heatmap).length.toString() },
            ]} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Growth Trend / Topic Mastery */}
              <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
                <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Topic Mastery</h2>
                <div className="space-y-3">
                  {Object.entries(progress.mastery_heatmap)
                    .sort(([, a], [, b]) => b - a)
                    .map(([topic, score]) => (
                      <div key={topic} className="flex items-center gap-3">
                        <span className="text-sm text-v2-text-secondary w-36 truncate shrink-0">{topic}</span>
                        <div className="flex-1 h-2 bg-v2-border rounded-full overflow-hidden">
                          <div className="h-full rounded-full bg-v2-accent transition-all duration-500" style={{ width: `${score}%` }} />
                        </div>
                        <span className="text-xs font-mono text-v2-text-secondary w-8 text-right">{score.toFixed(0)}</span>
                      </div>
                    ))}
                </div>
              </div>

              {/* Recent Quiz Results */}
              {progress.recent_quizzes.length > 0 && (
                <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
                  <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Recent Quiz Results</h2>
                  <div className="space-y-2">
                    {progress.recent_quizzes.slice(0, 10).map((q, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-v2-border/50 last:border-0">
                        <div>
                          <p className="text-sm text-v2-text-primary">{new Date(q.created_at).toLocaleDateString()}</p>
                          <p className="text-xs text-v2-text-secondary">{q.score}/{q.total} questions</p>
                        </div>
                        <span className={`text-sm font-mono ${q.total > 0 ? ((q.score / q.total) >= 0.7 ? 'text-v2-success' : (q.score / q.total) >= 0.4 ? 'text-v2-warning' : 'text-v2-error') : 'text-v2-text-secondary'}`}>
                          {q.total > 0 ? ((q.score / q.total) * 100).toFixed(0) : '0'}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-6">
              {/* Weekly Summary */}
              {summary && (
                <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
                  <h2 className="text-lg font-semibold text-v2-text-primary mb-2">Weekly Summary</h2>
                  <p className="text-xs text-v2-text-secondary mb-3">{summary.week_start} — {summary.week_end}</p>
                  {summary.is_low_performance_warning && (
                    <div className="p-3 rounded-xl bg-v2-warning/10 text-v2-warning text-sm font-medium mb-3">⚠️ Low performance</div>
                  )}
                  <p className="text-sm text-v2-text-primary leading-relaxed">{summary.summary_text}</p>
                </div>
              )}

              <AIInsightPanel insights={deriveParentInsights(progress, summary)} />
            </div>
          </div>
        </>
      ) : null}
    </>
  )
}
