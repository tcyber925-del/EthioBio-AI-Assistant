'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import {
  AlertTriangle,
  Award,
  BarChart3,
  BookOpen,
  Calendar,
  RefreshCw,
  TrendingUp,
  User,
  Zap,
} from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface ChildSummary {
  student_id: string
  name: string
  grade_level: number | null
  last_active: string | null
  overall_readiness: number
}

interface ChildProgress {
  student_id: string
  overall_readiness: number
  mastery_heatmap: Record<string, number>
  recent_quizzes: {
    quiz_id: string | null
    score: number
    total: number
    created_at: string
  }[]
  streak: number
  total_xp: number
}

interface WeeklySummary {
  summary_text: string
  summary_amharic: string | null
  week_start: string
  week_end: string
  is_low_performance_warning: boolean
}

function healthColor(score: number): string {
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-emerald-400'
  if (score >= 40) return 'text-yellow-400'
  return 'text-red-400'
}

function healthBg(score: number): string {
  if (score >= 80) return 'bg-green-500/10 border-green-500/20'
  if (score >= 60) return 'bg-emerald-500/10 border-emerald-500/20'
  if (score >= 40) return 'bg-yellow-500/10 border-yellow-500/20'
  return 'bg-red-500/10 border-red-500/20'
}

export default function ParentDashboardPage() {
  const router = useRouter()
  const [children, setChildren] = useState<ChildSummary[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [progress, setProgress] = useState<ChildProgress | null>(null)
  const [summary, setSummary] = useState<WeeklySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingProgress, setLoadingProgress] = useState(false)
  const [generatingSummary, setGeneratingSummary] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const locale = useLocale()
  const t = useTranslations('parent.dashboard')
  const tc = useTranslations('common')

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    fetchWithAuth('/api/parent/children')
      .then(data => {
        setChildren(data)
        if (data.length > 0) setSelectedId(data[0].student_id)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const loadProgress = useCallback((childId: string) => {
    setLoadingProgress(true)
    setError(null)
    fetchWithAuth(`/api/parent/children/${childId}/progress`)
      .then(setProgress)
      .catch(err => setError(err.message))
      .finally(() => setLoadingProgress(false))
  }, [])

  const loadSummary = useCallback((childId: string) => {
    fetchWithAuth(`/api/parent/children/${childId}/weekly-summary`)
      .then(setSummary)
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedId) {
      loadProgress(selectedId)
      loadSummary(selectedId)
    }
  }, [selectedId])

  const generateNewSummary = () => {
    if (!selectedId) return
    setGeneratingSummary(true)
    fetchWithAuth(`/api/parent/children/${selectedId}/weekly-summary?language=en`)
      .then(s => {
        setSummary(s)
        setGeneratingSummary(false)
      })
      .catch(() => setGeneratingSummary(false))
  }

  if (loading) {
    return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  }

  const selectedChild = children.find(c => c.student_id === selectedId)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <User className="w-6 h-6" />
            {t('title')}
          </h1>
          <p className="text-foreground-muted text-sm mt-1">{t('subtitle')}</p>
        </div>
        {children.length > 1 && (
          <select
            value={selectedId}
            onChange={e => setSelectedId(e.target.value)}
            className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground"
          >
            {children.map(c => (
              <option key={c.student_id} value={c.student_id}>{c.name}</option>
            ))}
          </select>
        )}
      </div>

      {children.length === 0 && !loading && (
        <div className="text-center py-16">
          <User className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">{t('no_children_title')}</p>
          <p className="text-xs text-foreground-muted mt-1">{t('no_children_subtitle')}</p>
        </div>
      )}

      {error && (
        <div className="text-center py-16">
          {error.includes('Parent access required') || error.includes('Parent access') ? (
            <>
              <User className="w-12 h-12 text-border mx-auto mb-3" />
              <p className="text-foreground-muted font-medium text-base">{t('parent_access_required')}</p>
              <p className="text-sm text-foreground-muted mt-2 max-w-md mx-auto leading-relaxed">
                {t('parent_access_desc')}
              </p>
              <a href="/login" className="inline-flex items-center gap-2 mt-5 px-5 py-2.5 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors">
                {t('switch_account')}
              </a>
            </>
          ) : (
            <>
              <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
              <p className="text-red-400 text-sm">{error}</p>
              <button onClick={() => selectedId && loadProgress(selectedId)} className="text-sm text-primary hover:underline mt-2 flex items-center gap-1 mx-auto">
                <RefreshCw className="w-3 h-3" /> {tc('retry')}
              </button>
            </>
          )}
        </div>
      )}

      {selectedChild && (
        <div className="mb-4 rounded-xl border border-border bg-card p-3 flex items-center gap-4 text-sm">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
            <User className="w-5 h-5 text-primary" />
          </div>
          <div>
            <p className="font-medium text-foreground">{selectedChild.name}</p>
            <p className="text-foreground-muted text-xs">
              {t('grade_label')} {selectedChild.grade_level || 'N/A'} &middot; {t('overall_readiness')}:{' '}
              <span className={healthColor(selectedChild.overall_readiness)}>
                {selectedChild.overall_readiness.toFixed(0)}
              </span>
            </p>
          </div>
        </div>
      )}

      {loadingProgress && (
        <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}</div>
      )}

      {!loadingProgress && !error && progress && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className={`rounded-xl border p-4 ${healthBg(progress.overall_readiness)}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">{t('overall_readiness')}</span>
                <BarChart3 className={`w-4 h-4 ${healthColor(progress.overall_readiness)}`} />
              </div>
              <p className={`text-2xl font-bold ${healthColor(progress.overall_readiness)}`}>
                {progress.overall_readiness.toFixed(0)}
              </p>
              <p className="text-xs text-foreground-muted mt-1">{t('exam_readiness')}</p>
            </div>

            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">{t('current_streak')}</span>
                <Zap className="w-4 h-4 text-yellow-400" />
              </div>
              <p className="text-2xl font-bold text-foreground">{progress.streak} days</p>
              <p className="text-xs text-foreground-muted mt-1">{progress.total_xp} {t('total_xp_label')}</p>
            </div>

            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">{t('topics_mastered')}</span>
                <Award className="w-4 h-4 text-primary" />
              </div>
              <p className="text-2xl font-bold text-foreground">{Object.keys(progress.mastery_heatmap).length}</p>
              <p className="text-xs text-foreground-muted mt-1">{t('topics_with_data')}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="rounded-xl border border-border bg-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-primary" />
                {t('mastery_by_topic')}
              </h3>
              {Object.keys(progress.mastery_heatmap).length === 0 ? (
                <p className="text-xs text-foreground-muted py-4 text-center">{t('no_mastery_data')}</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(progress.mastery_heatmap)
                    .sort(([, a], [, b]) => b - a)
                    .map(([topic, score]) => (
                      <div key={topic} className="flex items-center gap-3 text-xs">
                        <span className="text-foreground w-28 truncate shrink-0">{topic}</span>
                        <div className="flex-1 h-2 bg-background-secondary rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${score >= 80 ? 'bg-green-400' : score >= 60 ? 'bg-emerald-400' : score >= 40 ? 'bg-yellow-400' : 'bg-red-400'}`}
                            style={{ width: `${score}%` }}
                          />
                        </div>
                        <span className={`font-medium w-8 text-right ${healthColor(score)}`}>{score.toFixed(0)}</span>
                      </div>
                    ))}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border bg-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                {t('recent_quizzes')}
              </h3>
              {progress.recent_quizzes.length === 0 ? (
                <p className="text-xs text-foreground-muted py-4 text-center">{t('no_quizzes_taken')}</p>
              ) : (
                <div className="space-y-2">
                  {progress.recent_quizzes.map((q, i) => {
                    const pct = q.total > 0 ? (q.score / q.total) * 100 : 0
                    return (
                      <div key={i} className="flex items-center gap-3 text-xs">
                        <Calendar className="w-3 h-3 text-foreground-muted shrink-0" />
                        <span className="text-foreground-muted w-20 shrink-0">
                          {new Date(q.created_at).toLocaleDateString(locale)}
                        </span>
                        <div className="flex-1 h-2 bg-background-secondary rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${pct >= 80 ? 'bg-green-400' : pct >= 60 ? 'bg-emerald-400' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className={`font-medium w-12 text-right ${healthColor(pct)}`}>
                          {q.score}/{q.total}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Award className="w-4 h-4 text-primary" />
                {t('weekly_summary_title')}
              </h3>
              <button
                onClick={generateNewSummary}
                disabled={generatingSummary}
                className="text-xs px-3 py-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 transition-colors disabled:opacity-50"
              >
                {generatingSummary ? t('generating') : t('generate_new')}
              </button>
            </div>
            {summary ? (
              <div>
                <p className="text-xs text-foreground-muted mb-2">
                  {new Date(summary.week_start).toLocaleDateString(locale)} – {new Date(summary.week_end).toLocaleDateString(locale)}
                </p>
                {summary.is_low_performance_warning && (
                  <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 rounded-lg px-3 py-2 mb-3">
                    <AlertTriangle className="w-3 h-3 shrink-0" />
                    {t('performance_needs_attention')}
                  </div>
                )}
                <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">{summary.summary_text}</p>
                {summary.summary_amharic && (
                  <div className="mt-3 pt-3 border-t border-border">
                    <p className="text-xs text-foreground-muted mb-1">{t('amharic_summary')}</p>
                    <p className="text-sm text-foreground leading-relaxed">{summary.summary_amharic}</p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-foreground-muted py-4 text-center">{t('no_summary_hint')}</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
