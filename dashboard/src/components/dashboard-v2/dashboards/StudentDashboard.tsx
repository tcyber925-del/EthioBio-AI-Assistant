'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { BookOpen, AlertTriangle, RefreshCw, Lock, Star, TrendingUp, Target, ClipboardCheck, ChevronRight } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId } from '@/lib/auth'
import { HeroSection, InsightCard, MetricStrip, ActivityTimeline, AIInsightPanel, LearningProgress } from '@/components/dashboard-v2'
import { MisconceptionPanel } from '@/components/misconceptions/MisconceptionPanel'
import { getBioIcon, BIO_ICON_IDS } from '@/components/dashboard-v2/BioIcon'

interface StudentData {
  user: { id: string; email: string; grade_level: number | null; created_at: string | null }
  gamification: {
    total_xp: number; level: number; current_streak: number; longest_streak: number
    next_level_xp: number
    achievements: Array<{ id: string; title: string; description: string; icon: string; unlocked_at: string | null }>
  }
  readiness: { overall_readiness: number; readiness_band: string; topic_readiness: Record<string, number> }
  weak_topics: Array<{ topic: string; severity: string; average_score: number; attempt_count: number; misconceptions: string[] }>
  due_reviews: Array<{ topic: string; next_review_at: string; mastery_score: number; interval_days: number }>
  recent_activity: Array<{ type: string; description: string; created_at: string | null }>
}

type TFn = (key: string, values?: Record<string, string | number>) => string

function deriveInsights(data: StudentData, t: TFn): string[] {
  const insights: string[] = []
  if (data.weak_topics.length > 0) {
    const w = data.weak_topics[0]
    insights.push(t('insight_focus', { topic: w.topic, score: w.average_score.toFixed(0) }))
  }
  if (data.due_reviews.length > 0) {
    insights.push(t('insight_reviews_due', { count: data.due_reviews.length }))
  }
  if (data.gamification.longest_streak > 0 && data.gamification.current_streak < data.gamification.longest_streak) {
    insights.push(t('insight_best_streak', { days: data.gamification.longest_streak }))
  }
  if (data.gamification.current_streak >= 3) {
    insights.push(t('insight_streak', { days: data.gamification.current_streak }))
  }
  return insights
}

function buildMilestones(data: StudentData, t: TFn) {
  const m = [
    { label: t('milestone_first_review'), completed: data.gamification.total_xp > 0 },
    { label: t('milestone_streak3'), completed: data.gamification.current_streak >= 3 },
    { label: t('milestone_level5'), completed: data.gamification.level >= 5 },
  ]
  if (data.weak_topics.length > 0) {
    m.push({ label: t('milestone_strengthen', { topic: data.weak_topics[0].topic }), completed: false })
  }
  return m
}

interface RecentAttempt {
  id: string; title: string; score: number; total: number; correct: number; completed_at: string
}

function RecentQuizAttempts({ t }: { t: TFn }) {
  const [attempts, setAttempts] = useState<RecentAttempt[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchWithAuth('/api/quiz/attempts?limit=5')
      .then(r => r.json())
      .then(d => setAttempts(d.items || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading || attempts.length === 0) return null

  return (
    <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-v2-text-primary">{t('recent_quizzes')}</h2>
        <Link href="/quiz/history" className="text-xs text-v2-accent hover:underline flex items-center gap-1">
          {t('view_all')} <ChevronRight className="w-3 h-3" />
        </Link>
      </div>
      <div className="space-y-2">
        {attempts.map(a => (
          <Link key={a.id} href={`/quiz/history/${a.id}`} className="flex items-center gap-3 p-3 rounded-xl bg-v2-bg hover:bg-v2-bg/80 transition-colors">
            <div className={`p-2 rounded-lg ${a.score >= 80 ? 'bg-green-500/10 text-green-400' : a.score >= 50 ? 'bg-yellow-500/10 text-yellow-400' : 'bg-red-500/10 text-red-400'}`}>
              <ClipboardCheck className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-v2-text-primary truncate">{a.title}</p>
              <p className="text-xs text-v2-text-secondary">{a.correct}/{a.total} correct</p>
            </div>
            <span className={`text-sm font-bold ${a.score >= 80 ? 'text-green-400' : a.score >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
              {Math.round(a.score)}%
            </span>
          </Link>
        ))}
      </div>
    </div>
  )
}

function userName(data: StudentData): string {
  return data.user.email ? data.user.email.split('@')[0] : 'there'
}

export function StudentDashboard() {
  const t = useTranslations('v2.student')
  const tc = useTranslations('common')
  const [data, setData] = useState<StudentData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true); setError(null)
    try {
      const response = await fetchWithAuth('/api/student/dashboard')
      const d = await response.json()
      setData(d)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const retry = () => fetchData()

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin mx-auto" />
          <p className="mt-3 text-sm text-v2-text-secondary">{t('loading')}</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-sm">
          <AlertTriangle className="w-10 h-10 text-v2-error mx-auto mb-3" />
          <p className="text-sm font-medium text-v2-error">{tc('error')}</p>
          <p className="text-xs text-v2-text-secondary mt-1 mb-4">{error}</p>
          <button onClick={retry} className="inline-flex items-center gap-2 px-4 h-9 rounded-xl bg-v2-accent text-v2-inverted text-sm font-medium hover:bg-white transition-colors">
            <RefreshCw className="w-4 h-4" /> {tc('retry')}
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  const userId = getUserId()
  const { gamification, readiness, weak_topics, recent_activity } = data
  const sortedTopics = Object.entries(readiness.topic_readiness).sort(([, a], [, b]) => b - a)
  const continueTopic = weak_topics[0]
  const insights = deriveInsights(data, t)
  const milestones = buildMilestones(data, t)

  return (
    <>
      <HeroSection
        title={t('welcome_back', { name: userName(data) })}
        subtitle={continueTopic
          ? t('hero_subtitle_focus', { topic: continueTopic.topic, score: continueTopic.average_score.toFixed(0) })
          : t('hero_subtitle_readiness', { pct: readiness.overall_readiness.toFixed(0) })
        }
        action={continueTopic ? { label: t('action_review', { topic: continueTopic.topic }), href: '/v2/lessons' } : undefined}
        secondary={readiness.overall_readiness >= 80
          ? <span><Star className="inline h-4 w-4 mr-1.5 text-v2-accent" />{t('badge_strong')}</span>
          : readiness.overall_readiness >= 50
          ? <span><TrendingUp className="inline h-4 w-4 mr-1.5 text-v2-accent" />{t('badge_steady')}</span>
          : <span><Target className="inline h-4 w-4 mr-1.5 text-v2-accent" />{t('badge_focused')}</span>}
      />

      {continueTopic && (
        <div className="mb-6">
          <div className="bg-v2-surface rounded-[20px] border border-v2-accent/30 p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-v2-accent-muted text-v2-accent">
                  <BookOpen className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs font-medium text-v2-text-secondary uppercase tracking-wider">{t('continue_learning')}</p>
                  <h3 className="mt-1 text-xl font-semibold text-v2-text-primary">{continueTopic.topic}</h3>
                  <p className="mt-1 text-sm text-v2-text-secondary">
                    {continueTopic.misconceptions.length > 0
                      ? t('address_misconception', { misconception: continueTopic.misconceptions[0] })
                      : t('review_mastery', { pct: continueTopic.average_score.toFixed(0) })
                    }
                  </p>
                  <div className="mt-3 h-1.5 w-48 bg-v2-border rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-v2-accent transition-all duration-500" style={{ width: `${continueTopic.average_score}%` }} />
                  </div>
                </div>
              </div>
              <span className="text-sm font-medium text-v2-accent">{continueTopic.average_score.toFixed(0)}%</span>
            </div>
          </div>
        </div>
      )}

      <div className="mb-6">
        <MetricStrip metrics={[
          { label: t('metric_readiness'), value: `${readiness.overall_readiness.toFixed(0)}%`, accent: true },
          { label: t('metric_xp'), value: gamification.total_xp.toLocaleString() },
          { label: t('metric_streak'), value: t('streak_days', { count: gamification.current_streak }) },
          { label: t('metric_level'), value: gamification.level.toString() },
        ]} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 space-y-6">
          <LearningProgress title={t('weekly_progress')} percent={readiness.overall_readiness} milestones={milestones} />

          {sortedTopics.length > 0 && (
            <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
              <h2 className="text-lg font-semibold text-v2-text-primary mb-4">{t('topic_mastery')}</h2>
              <div className="space-y-3">
                {sortedTopics.map(([topic, score]) => (
                  <div key={topic} className="flex items-center gap-3">
                    <span className="text-sm text-v2-text-secondary w-32 truncate shrink-0">{topic}</span>
                    <div className="flex-1 h-2 bg-v2-border rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-v2-accent transition-all duration-500" style={{ width: `${score}%` }} />
                    </div>
                    <span className="text-xs font-mono text-v2-text-secondary w-8 text-right">{score.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <RecentQuizAttempts t={t} />

          {weak_topics.length > 0 && (
            <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
              <h2 className="text-lg font-semibold text-v2-text-primary mb-4">{t('areas_to_improve', { count: weak_topics.length })}</h2>
              <div className="space-y-2">
                {weak_topics.slice(0, 5).map(wt => (
                  <div key={wt.topic} className="p-3 rounded-xl bg-v2-bg">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-medium text-v2-text-primary">{wt.topic}</span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${wt.severity === 'critical' ? 'bg-v2-error/10 text-v2-error' : wt.severity === 'moderate' ? 'bg-v2-warning/10 text-v2-warning' : 'bg-v2-accent-muted text-v2-accent'}`}>{wt.severity}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-v2-text-secondary">
                      <span>{t('score_label', { pct: wt.average_score.toFixed(0) })}</span>
                      <span>{t('attempts_label', { count: wt.attempt_count })}</span>
                    </div>
                    {wt.misconceptions.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {wt.misconceptions.map((mc, i) => (
                          <span key={i} className="px-2 py-0.5 rounded-md bg-v2-warning/5 text-v2-warning/80 text-xs">{mc}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {recent_activity.length > 0 && (
            <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
              <ActivityTimeline items={recent_activity} />
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-v2-accent-muted text-v2-accent"><BookOpen className="w-5 h-5" /></div>
              <div>
                <p className="text-xs text-v2-text-secondary">{t('achievements')}</p>
                <p className="text-xl font-bold text-v2-text-primary">
                  {gamification.achievements.filter(a => a.unlocked_at).length}
                  <span className="text-sm font-normal text-v2-text-secondary">/{gamification.achievements.length}</span>
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {gamification.achievements.map((a, i) => {
                const unlocked = !!a.unlocked_at
                const Icon = getBioIcon(BIO_ICON_IDS[i % BIO_ICON_IDS.length])
                return (
                  <div key={a.id} className={`p-3 rounded-xl text-center transition-all ${unlocked ? 'bg-v2-accent-muted border border-v2-accent/20' : 'bg-v2-bg border border-v2-border/50 opacity-50'}`}>
                    <div className={`w-7 h-7 mx-auto mb-1 ${unlocked ? 'text-v2-accent' : 'text-v2-text-secondary/40'}`}>
                      {unlocked ? <Icon className="w-full h-full" /> : <Lock className="w-full h-full" />}
                    </div>
                    <p className={`text-xs font-medium ${unlocked ? 'text-v2-text-primary' : 'text-v2-text-secondary'}`}>{a.title}</p>
                  </div>
                )
              })}
            </div>
          </div>
          {userId && <MisconceptionPanel userId={userId} />}
          <AIInsightPanel insights={insights} />
        </div>
      </div>
    </>
  )
}
