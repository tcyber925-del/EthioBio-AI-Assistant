'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import {
  Activity,
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
import { isAuthenticated } from '@/lib/auth'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { CardSkeleton } from '@/components/Skeleton'
import PageHeader from '@/components/ui/PageHeader'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

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

function severityBadgeVariant(severity: string) {
  switch (severity) {
    case 'critical': return 'red' as const
    case 'moderate': return 'yellow' as const
    case 'mild': return 'blue' as const
    default: return 'muted' as const
  }
}

export default function StudentDashboardPage() {
  const router = useRouter()
  const [data, setData] = useState<StudentDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)
  const locale = useLocale()
  const t = useTranslations('student.dashboard')
  const tc = useTranslations('common')

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchWithAuth('/api/student/dashboard')
      const d = await response.json()
      setData(d)
    } catch (err: unknown) {
      setError(normalizeException(err))
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
        <div className="h-16 mb-8">
          <div className="animate-pulse bg-border/50 rounded-lg w-48 h-8" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <CardSkeleton />
            <CardSkeleton />
          </div>
          <div className="space-y-6">
            <CardSkeleton />
            <CardSkeleton />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <ErrorState
        error={error}
        title={tc('error')}
        onRetry={() => void fetchData()}
      />
    )
  }

  if (!data) return null

  const { gamification, readiness, weak_topics, due_reviews, recent_activity } = data
  const sortedTopics = Object.entries(readiness.topic_readiness).sort(([, a], [, b]) => a - b)
  const isEmpty = !gamification.total_xp && !gamification.current_streak && weak_topics.length === 0

  return (
    <div>
      <PageHeader
        icon={<User className="w-6 h-6" />}
        title={t('title')}
        description={data.user.grade_level
          ? `${t('grade_with_level', { grade: data.user.grade_level })} · ${t('welcome_back')}`
          : t('welcome_back')
        }
        actions={
          <Button variant="secondary" size="sm" onClick={fetchData}>
            <RefreshCw className="w-4 h-4" />
            {tc('refresh')}
          </Button>
        }
      />

      {isEmpty ? (
        <Card className="text-center py-16">
          <Sparkles className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted text-subhead font-medium">{t('no_learning_data')}</p>
          <p className="text-small text-foreground-muted/60 mt-1 max-w-md mx-auto">
            {t('no_learning_desc')}
          </p>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
            <Card>
              <div className="flex items-center justify-between mb-2">
                <span className="text-small text-foreground-muted font-medium">{t('total_xp')}</span>
                <Trophy className="w-4 h-4 text-accent-gold" />
              </div>
              <p className="text-display text-foreground">{gamification.total_xp}</p>
              <p className="text-small text-foreground-muted mt-1">{t('level')} {gamification.level}</p>
            </Card>

            <Card>
              <div className="flex items-center justify-between mb-2">
                <span className="text-small text-foreground-muted font-medium">{t('streak')}</span>
                <Zap className="w-4 h-4 text-accent-gold" />
              </div>
              <p className="text-display text-foreground">{gamification.current_streak} <span className="text-subhead text-foreground-muted">{t('days')}</span></p>
              <p className="text-small text-foreground-muted mt-1">{t('best')} {gamification.longest_streak}</p>
            </Card>

            <Card className={healthBg(readiness.overall_readiness)}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-small text-foreground-muted font-medium">{t('readiness')}</span>
                <BarChart3 className={`w-4 h-4 ${healthColor(readiness.overall_readiness)}`} />
              </div>
              <p className={`text-display ${healthColor(readiness.overall_readiness)}`}>
                {readiness.overall_readiness.toFixed(0)}
              </p>
              <p className="text-small text-foreground-muted mt-1">{readiness.readiness_band}</p>
            </Card>

            <Card>
              <div className="flex items-center justify-between mb-2">
                <span className="text-small text-foreground-muted font-medium">{t('achievements')}</span>
                <Award className="w-4 h-4 text-primary" />
              </div>
              <p className="text-display text-foreground">
                {gamification.achievements.length}
              </p>
              <p className="text-small text-foreground-muted mt-1">{t('achievements')}</p>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="lg:col-span-2 space-y-6">
              {sortedTopics.length > 0 && (
                <Card variant="accent">
                  <h2 className="text-subhead text-foreground mb-5 flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-primary" />
                    {t('topic_mastery')}
                  </h2>
                  <div className="space-y-3">
                    {sortedTopics.map(([topic, score]) => (
                      <div key={topic} className="flex items-center gap-3">
                        <span className="text-small text-foreground-muted w-32 truncate shrink-0">{topic}</span>
                        <div className="flex-1 h-2 bg-background-secondary rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              score >= 80 ? 'bg-green-400' : score >= 60 ? 'bg-emerald-400' : score >= 40 ? 'bg-yellow-400' : 'bg-red-400'
                            }`}
                            style={{ width: `${score}%` }}
                          />
                        </div>
                        <span className={`text-subhead font-mono w-10 text-right ${healthColor(score)}`}>
                          {score.toFixed(0)}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {weak_topics.length > 0 && (
                <Card variant="accent" className="border-t-red-500/50">
                  <h2 className="text-subhead text-foreground mb-5 flex items-center gap-2">
                    <Target className="w-4 h-4 text-red-400" />
                    {t('areas_to_improve')} ({weak_topics.length})
                  </h2>
                  <div className="space-y-3">
                    {weak_topics.slice(0, 5).map(wt => (
                      <div key={wt.topic} className="p-4 rounded-lg bg-background-secondary/50 border border-border">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-subhead text-foreground">{wt.topic}</span>
                          <Badge variant={severityBadgeVariant(wt.severity)}>
                            {wt.severity}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 text-small text-foreground-muted">
                          <span>{t('score')}: {wt.average_score.toFixed(0)}%</span>
                          <span>{t('attempts')}: {wt.attempt_count}</span>
                        </div>
                        {wt.misconceptions.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {wt.misconceptions.map((mc, i) => (
                              <span key={i} className="px-2 py-0.5 bg-red-500/5 text-red-400/80 rounded text-small">
                                {mc}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {recent_activity.length > 0 && (
                <Card>
                  <h2 className="text-subhead text-foreground mb-5 flex items-center gap-2">
                    <Activity className="w-4 h-4 text-primary" />
                    {t('recent_activity')}
                  </h2>
                  <div className="space-y-1">
                    {recent_activity.slice(0, 10).map((item, i) => (
                      <div key={i} className="flex items-center gap-3 text-body py-2.5 border-b border-border/50 last:border-0">
                        {item.type === 'xp' ? (
                          <Zap className="w-4 h-4 text-accent-gold shrink-0" />
                        ) : (
                          <TrendingUp className="w-4 h-4 text-primary shrink-0" />
                        )}
                        <span className="text-foreground flex-1">{item.description}</span>
                        <span className="text-small text-foreground-muted shrink-0">
                          {item.created_at ? new Date(item.created_at).toLocaleDateString(locale) : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>

            <div className="space-y-6">
              {due_reviews.length > 0 && (
                <Card>
                  <h2 className="text-subhead text-foreground mb-5 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-primary" />
                    {t('due_reviews')} ({due_reviews.length})
                  </h2>
                  <div className="space-y-1">
                    {due_reviews.map(dr => (
                      <div key={dr.topic} className="flex items-center justify-between p-3 rounded-lg hover:bg-background-secondary transition-colors cursor-pointer group">
                        <div>
                          <p className="text-body text-foreground">{dr.topic}</p>
                          <p className="text-small text-foreground-muted mt-0.5">
                            {t('mastery_label')} {dr.mastery_score.toFixed(0)}% · {dr.interval_days}d
                          </p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-foreground-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {gamification.achievements.length > 0 && (
                <Card>
                  <h2 className="text-subhead text-foreground mb-5 flex items-center gap-2">
                    <Award className="w-4 h-4 text-primary" />
                    {t('recent_achievements')}
                  </h2>
                  <div className="space-y-2">
                    {gamification.achievements.slice(0, 5).map(a => (
                      <div key={a.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-background-secondary transition-colors">
                        <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                          <Trophy className="w-4 h-4 text-primary" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-body font-medium text-foreground truncate">{a.title}</p>
                          <p className="text-small text-foreground-muted truncate">{a.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
