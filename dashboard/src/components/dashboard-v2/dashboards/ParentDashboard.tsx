'use client'

import { useEffect, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { HeroSection, InsightCard, MetricStrip, AIInsightPanel, LearningProgress } from '@/components/dashboard-v2'
import { ErrorState, ErrorBanner } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

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

type TFn = (key: string, values?: Record<string, string | number>) => string

function deriveParentInsights(progress: ChildProgress, summary: WeeklySummary | null, t: TFn): string[] {
  const insights: string[] = []
  const topics = Object.entries(progress.mastery_heatmap)
  const weak = topics.filter(([, s]) => s < 50)
  const strong = topics.filter(([, s]) => s >= 80)
  if (weak.length > 0) insights.push(t('insight_weak', { count: weak.length, topics: weak.map(([tp]) => tp).join(', ') }))
  if (strong.length > 0) insights.push(t('insight_strong', { count: strong.length, topics: strong.map(([tp]) => tp).join(', ') }))
  if (summary?.is_low_performance_warning) insights.push(t('insight_warning'))
  if (progress.streak >= 3) insights.push(t('insight_streak', { days: progress.streak }))
  return insights
}

export function ParentDashboard() {
  const t = useTranslations('v2.parent')
  const ts = useTranslations('v2.student')
  const tc = useTranslations('common')
  const [children, setChildren] = useState<ChildSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [progress, setProgress] = useState<ChildProgress | null>(null)
  const [summary, setSummary] = useState<WeeklySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)
  const [progressLoading, setProgressLoading] = useState(false)
  const [progressError, setProgressError] = useState<AppError | null>(null)

  const fetchChildren = async () => {
    setLoading(true); setError(null)
    try {
      const response = await fetchWithAuth('/api/parent/children')
      const d = await response.json()
      setChildren(d.children || [])
      if (d.children?.length > 0) {
        setSelectedId(d.children[0].student_id)
      }
    } catch (err) {
      setError(normalizeException(err))
    } finally { setLoading(false) }
  }

  const fetchProgress = async (studentId: string) => {
    setProgressLoading(true)
    setProgress(null)
    setSummary(null)
    setProgressError(null)
    try {
      const [p, s] = await Promise.allSettled([
        fetchWithAuth(`/api/parent/children/${studentId}/progress`).then(r => r.json()),
        fetchWithAuth(`/api/parent/children/${studentId}/weekly-summary`).then(r => r.json()),
      ])
      if (p.status === 'fulfilled') setProgress(p.value)
      else setProgressError(normalizeException(p.reason))
      if (s.status === 'fulfilled') setSummary(s.value)
      else setProgressError(normalizeException(s.reason))
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
    return <ErrorState error={error} title={t('load_error')} onRetry={() => void fetchChildren()} />
  }

  const child = children.find(c => c.student_id === selectedId)

  return (
    <>
      <HeroSection
        title={t('title')}
        subtitle={child ? t('subtitle_child', { name: child.name, grade: child.grade_level || 'N/A' }) : t('subtitle_select')}
        secondary={child && progress ? t('secondary_stats', { xp: progress.total_xp, days: progress.streak }) : undefined}
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
          <p className="text-sm text-v2-text-secondary">{t('no_children')}</p>
        </div>
      ) : progressLoading ? (
        <div className="flex items-center justify-center h-48">
          <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin mx-auto" />
        </div>
      ) : (
        <>
          {progressError && (
            <div className="mb-6">
              <ErrorBanner error={progressError} actionLabel={tc('retry')} onAction={() => void (selectedId && fetchProgress(selectedId))} />
            </div>
          )}
          {progress ? (
            <>
              <div className="mb-6">
                <MetricStrip metrics={[
                  { label: ts('metric_readiness'), value: `${progress.overall_readiness.toFixed(0)}%`, accent: true },
                  { label: ts('metric_xp'), value: progress.total_xp.toLocaleString() },
                  { label: ts('metric_streak'), value: ts('streak_days', { count: progress.streak }) },
                  { label: t('metric_topics'), value: Object.keys(progress.mastery_heatmap).length.toString() },
                ]} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
                <div className="lg:col-span-2 space-y-6">
                  {/* Growth Trend / Topic Mastery */}
                  <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
                    <h2 className="text-lg font-semibold text-v2-text-primary mb-4">{ts('topic_mastery')}</h2>
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
                      <h2 className="text-lg font-semibold text-v2-text-primary mb-4">{t('recent_quiz_results')}</h2>
                      <div className="space-y-2">
                        {progress.recent_quizzes.slice(0, 10).map((q, i) => (
                          <div key={i} className="flex items-center justify-between py-2 border-b border-v2-border/50 last:border-0">
                            <div>
                              <p className="text-sm text-v2-text-primary">{new Date(q.created_at).toLocaleDateString()}</p>
                              <p className="text-xs text-v2-text-secondary">{t('questions_label', { score: q.score, total: q.total })}</p>
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
                      <h2 className="text-lg font-semibold text-v2-text-primary mb-2">{t('weekly_summary')}</h2>
                      <p className="text-xs text-v2-text-secondary mb-3">{summary.week_start} — {summary.week_end}</p>
                      {summary.is_low_performance_warning && (
                        <div className="p-3 rounded-xl bg-v2-warning/10 text-v2-warning text-sm font-medium mb-3">⚠️ {t('low_performance')}</div>
                      )}
                      <p className="text-sm text-v2-text-primary leading-relaxed">{summary.summary_text}</p>
                    </div>
                  )}

                  <AIInsightPanel insights={deriveParentInsights(progress, summary, t)} />
                </div>
              </div>
            </>
          ) : null}
        </>
      )}
    </>
  )
}
