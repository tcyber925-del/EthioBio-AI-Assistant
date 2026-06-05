'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import {
  Activity,
  AlertTriangle,
  Award,
  BarChart3,
  BookOpen,
  Calendar,
  ChevronRight,
  RefreshCw,
  Sparkles,
  Target,
  TrendingUp,
  Trophy,
  User,
  Zap,
} from 'lucide-react'
import { getUserRole, isAuthenticated } from '@/lib/auth'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { CardSkeleton } from '@/components/Skeleton'

export const dynamic = 'force-dynamic'

interface StudentDashboard {
  user: { id: string; email: string; grade_level: number | null; created_at: string | null }
  gamification: {
    total_xp: number; level: number; current_streak: number; longest_streak: number
    next_level_xp: number; achievements: Array<{ id: string; title: string; description: string; icon: string; unlocked_at: string | null }>
  }
  readiness: { overall_readiness: number; readiness_band: string; topic_readiness: Record<string, number> }
  weak_topics: Array<{ topic: string; severity: string; average_score: number; attempt_count: number; misconceptions: string[] }>
  due_reviews: Array<{ topic: string; next_review_at: string; mastery_score: number; interval_days: number }>
  recent_activity: Array<{ type: string; description: string; created_at: string | null }>
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

function severityBadge(severity: string) {
  const colors: Record<string, string> = {
    critical: 'bg-red-500/10 text-red-400',
    moderate: 'bg-yellow-500/10 text-yellow-400',
    mild: 'bg-blue-500/10 text-blue-400',
  }
  return colors[severity] || 'bg-border/50 text-foreground-muted'
}

export default function StudentDashboardPage() {
  const router = useRouter()
  const [data, setData] = useState<StudentDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const locale = useLocale()
  const t = useTranslations('student.dashboard')
  const tc = useTranslations('common')

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await fetchWithAuth('/api/student/dashboard')
      setData(d)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchData()
  }, [router])

  if (loading && !data) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-foreground mb-6">{t('title')}</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
          {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <p className="text-red-400 font-medium">{tc('error')}</p>
          <p className="text-sm text-foreground-muted mt-1">{error}</p>
          <button onClick={fetchData} className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
            {tc('retry')}
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  const { gamification, readiness, weak_topics, due_reviews, recent_activity } = data
  const sortedTopics = Object.entries(readiness.topic_readiness).sort(([, a], [, b]) => a - b)
  const isEmpty = !gamification.total_xp && !gamification.current_streak && weak_topics.length === 0

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <User className="w-6 h-6 text-primary" />
            {t('title')}
          </h1>
          <p className="text-sm text-foreground-muted mt-1">
            {data.user.grade_level ? `Grade ${data.user.grade_level} · ` : ''}
            {t('welcome_back')}
          </p>
        </div>
        <button onClick={fetchData} className="flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-lg hover:bg-card transition-colors text-foreground-muted hover:text-foreground">
          <RefreshCw className="w-4 h-4" /> {tc('refresh')}
        </button>
      </div>

      {isEmpty ? (
        <div className="text-center py-16 bg-card rounded-xl border border-border">
          <Sparkles className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">{t('no_learning_data')}</p>
          <p className="text-sm text-foreground-muted/60 mt-1 max-w-md mx-auto">
            {t('no_learning_desc')}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-card rounded-xl border border-border p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">{t('total_xp')}</span>
                <Trophy className="w-4 h-4 text-yellow-400" />
              </div>
              <p className="text-2xl font-bold text-foreground">{gamification.total_xp}</p>
              <p className="text-xs text-foreground-muted mt-1">{t('level')} {gamification.level}</p>
            </div>

            <div className="bg-card rounded-xl border border-border p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">{t('streak')}</span>
                <Zap className="w-4 h-4 text-yellow-400" />
              </div>
              <p className="text-2xl font-bold text-foreground">{gamification.current_streak} {t('days')}</p>
              <p className="text-xs text-foreground-muted mt-1">{t('best')} {gamification.longest_streak}</p>
            </div>

            <div className={`rounded-xl border p-4 ${healthBg(readiness.overall_readiness)}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">{t('readiness')}</span>
                <BarChart3 className={`w-4 h-4 ${healthColor(readiness.overall_readiness)}`} />
              </div>
              <p className={`text-2xl font-bold ${healthColor(readiness.overall_readiness)}`}>
                {readiness.overall_readiness.toFixed(0)}
              </p>
              <p className="text-xs text-foreground-muted mt-1">{readiness.readiness_band}</p>
            </div>

            <div className="bg-card rounded-xl border border-border p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">{t('achievements')}</span>
                <Award className="w-4 h-4 text-primary" />
              </div>
              <p className="text-2xl font-bold text-foreground">
                {gamification.achievements.length}
              </p>
              <p className="text-xs text-foreground-muted mt-1">{t('achievements')}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="lg:col-span-2 space-y-6">
              {sortedTopics.length > 0 && (
                <div className="bg-card rounded-xl border border-border p-5">
                  <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-primary" />
                    {t('topic_mastery')}
                  </h2>
                  <div className="space-y-2">
                    {sortedTopics.map(([topic, score]) => (
                      <div key={topic} className="flex items-center gap-3 text-sm">
                        <span className="text-foreground-muted w-32 truncate shrink-0">{topic}</span>
                        <div className="flex-1 h-2.5 bg-background-secondary rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              score >= 80 ? 'bg-green-400' : score >= 60 ? 'bg-emerald-400' : score >= 40 ? 'bg-yellow-400' : 'bg-red-400'
                            }`}
                            style={{ width: `${score}%` }}
                          />
                        </div>
                        <span className={`font-medium w-10 text-right ${healthColor(score)}`}>
                          {score.toFixed(0)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {weak_topics.length > 0 && (
                <div className="bg-card rounded-xl border border-border p-5">
                  <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                    <Target className="w-4 h-4 text-red-400" />
                    {t('areas_to_improve')} ({weak_topics.length})
                  </h2>
                  <div className="space-y-3">
                    {weak_topics.slice(0, 5).map(wt => (
                      <div key={wt.topic} className="p-3 rounded-lg bg-background-secondary/50 border border-border">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-foreground text-sm">{wt.topic}</span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${severityBadge(wt.severity)}`}>
                            {wt.severity}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-foreground-muted">
                          <span>{t('score')}: {wt.average_score.toFixed(0)}%</span>
                          <span>{t('attempts')}: {wt.attempt_count}</span>
                        </div>
                        {wt.misconceptions.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {wt.misconceptions.map((mc, i) => (
                              <span key={i} className="px-2 py-0.5 bg-red-500/5 text-red-400/80 rounded text-xs">
                                {mc}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {recent_activity.length > 0 && (
                <div className="bg-card rounded-xl border border-border p-5">
                  <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-primary" />
                    {t('recent_activity')}
                  </h2>
                  <div className="space-y-2">
                    {recent_activity.slice(0, 10).map((item, i) => (
                      <div key={i} className="flex items-center gap-3 text-sm py-2 border-b border-border/50 last:border-0">
                        {item.type === 'xp' ? (
                          <Zap className="w-4 h-4 text-yellow-400 shrink-0" />
                        ) : (
                          <TrendingUp className="w-4 h-4 text-primary shrink-0" />
                        )}
                        <span className="text-foreground flex-1">{item.description}</span>
                        <span className="text-xs text-foreground-muted shrink-0">
                          {item.created_at ? new Date(item.created_at).toLocaleDateString(locale) : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-6">
              {due_reviews.length > 0 && (
                <div className="bg-card rounded-xl border border-border p-5">
                  <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-primary" />
                    {t('due_reviews')} ({due_reviews.length})
                  </h2>
                  <div className="space-y-2">
                    {due_reviews.map(dr => (
                      <div key={dr.topic} className="flex items-center justify-between p-2 rounded-lg hover:bg-background-secondary transition-colors">
                        <div>
                          <p className="text-sm text-foreground">{dr.topic}</p>
                          <p className="text-xs text-foreground-muted">
                            {t('mastery_label')} {dr.mastery_score.toFixed(0)}% · {dr.interval_days}d
                          </p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-foreground-muted" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {gamification.achievements.length > 0 && (
                <div className="bg-card rounded-xl border border-border p-5">
                  <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
                    <Award className="w-4 h-4 text-primary" />
                    {t('recent_achievements')}
                  </h2>
                  <div className="space-y-2">
                    {gamification.achievements.slice(0, 5).map(a => (
                      <div key={a.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-background-secondary transition-colors">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <Trophy className="w-4 h-4 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">{a.title}</p>
                          <p className="text-xs text-foreground-muted truncate">{a.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
