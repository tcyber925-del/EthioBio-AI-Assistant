'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { Activity, ClipboardList, AlertTriangle, Loader2, Search, CheckCircle2, Clock, BookOpen, Lightbulb, ArrowRight, Target, Brain, TrendingUp, RotateCcw, Bell, PartyPopper, Sparkles, RefreshCw } from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { CardSkeleton } from '@/components/Skeleton'
import { isAuthenticated } from '@/lib/auth'
import { MasteryRadarChart } from '@/components/recovery/MasteryRadarChart'
import { TopicHeatmap } from '@/components/recovery/TopicHeatmap'
import { LearningTree } from '@/components/recovery/LearningTree'
import PageHeader from '@/components/ui/PageHeader'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'

export const dynamic = 'force-dynamic'

interface Misconception {
  pattern_type: string
  description: string
  frequency: number
}

interface WeakTopic {
  topic: string
  unit: string
  grade_level: number
  average_score: number
  attempt_count: number
  severity: string
  confidence: number
  misconceptions: Misconception[]
  last_assessed_at: string | null
}

interface RecoveryTask {
  id: string
  plan_id: string
  title: string
  task_type: string
  description: string | null
  is_completed: boolean
  completed_at: string | null
  xp_awarded: number
  created_at: string
}

interface RecoveryPlan {
  id: string
  user_id: string
  topic: string
  total_tasks: number
  completed_tasks: number
  status: string
  progress_pct: number
  tasks: RecoveryTask[]
  created_at: string
  updated_at: string
}

interface MasteryHistoryPoint {
  average_score: number
  source: string
  recorded_at: string
}

interface TopicHistory {
  [topic: string]: MasteryHistoryPoint[]
}

interface Recommendation {
  type: string
  message: string
  priority: string
}

interface DueReview {
  id: string
  topic: string
  unit: string
  grade_level: number
  mastery_score: number
  interval_days: number
  ease_factor: number
  next_review_at: string
  last_reviewed_at: string | null
  review_count: number
  is_due: boolean
  days_overdue: number
}

interface Notification {
  id: string
  topic: string
  event_type: string
  message: string
  improvement_pct: number | null
  is_read: boolean
  created_at: string
}

interface DashboardData {
  user_id: string
  weak_topics: WeakTopic[]
  total_weak_topics: number
  active_plans: RecoveryPlan[]
  total_active_plans: number
  recommendations: Recommendation[]
  due_reviews: DueReview[]
  total_due_reviews: number
  unread_notifications: number
  notifications: Notification[]
}

interface Student {
  id: string
  telegram_id: number | null
  role: string
  language_preference: string
  grade_level: number | null
  created_at: string
}

const severityBadgeVariant = (severity: string) => {
  switch (severity) {
    case 'critical': return 'red' as const
    case 'moderate': return 'yellow' as const
    case 'mild': return 'blue' as const
    default: return 'muted' as const
  }
}

const notificationIconColor = (eventType: string) => {
  switch (eventType) {
    case 'mastery_improvement': return 'text-green-400 bg-green-500/10'
    case 'severity_upgrade': return 'text-purple-400 bg-purple-500/10'
    case 'plan_completed': return 'text-blue-400 bg-blue-500/10'
    default: return 'text-yellow-400 bg-yellow-500/10'
  }
}

const notificationIconName = (eventType: string) => {
  switch (eventType) {
    case 'mastery_improvement': return TrendingUp
    case 'severity_upgrade': return PartyPopper
    case 'plan_completed': return Sparkles
    default: return Bell
  }
}

const priorityBorder = (priority: string) => {
  switch (priority) {
    case 'high': return 'border-l-red-500 bg-red-500/5'
    case 'medium': return 'border-l-yellow-500 bg-yellow-500/5'
    default: return 'border-l-blue-500 bg-blue-500/5'
  }
}

const SimpleMiniChart = ({ points, topic }: { points: MasteryHistoryPoint[]; topic: string }) => {
  if (!points || points.length < 2) return null
  const width = 200; const height = 48
  const values = points.map(p => p.average_score)
  const mn = Math.min(...values); const mx = Math.max(...values)
  const range = Math.max(mx - mn, 10); const pad = 4
  const pts = values.map((v, i) => {
    const x = pad + (i / Math.max(values.length - 1, 1)) * (width - 2 * pad)
    const y = height - pad - ((v - mn) / range) * (height - 2 * pad)
    return `${x},${y}`
  }).join(' ')
  const lastVal = values[values.length - 1]
  const firstVal = values[0]

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between text-small text-foreground-muted mb-1">
        <span>Progress over time</span>
        <span className={lastVal > firstVal ? 'text-green-400' : lastVal < firstVal ? 'text-red-400' : ''}>
          {firstVal.toFixed(0)}% → {lastVal.toFixed(0)}%
        </span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-12">
        <polyline
          points={pts}
          fill="none"
          stroke={lastVal > firstVal ? '#34d399' : lastVal < firstVal ? '#ef4444' : '#8896b8'}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  )
}

const taskTypeIcon = (type: string) => {
  switch (type) {
    case 'review_notes': return BookOpen
    case 'guided_quiz': return Target
    case 'diagram_exercise': return Brain
    default: return ClipboardList
  }
}

export default function RecoveryPage() {
  const router = useRouter()
  const [userId, setUserId] = useState('')
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<TopicHistory>({})
  const [historyLoading, setHistoryLoading] = useState(false)
  const [students, setStudents] = useState<Student[]>([])
  const [studentsLoading, setStudentsLoading] = useState(true)
  const [notificationsExpanded, setNotificationsExpanded] = useState(false)
  const locale = useLocale()
  const t = useTranslations('recovery')
  const tc = useTranslations('common')

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchDashboardData()
  }, [router])

  const fetchDashboardData = async () => {
    setStudentsLoading(true)
    try {
      const d = await fetchWithAuth('/api/teacher/students')
      setStudents(d || [])
    } catch (err: unknown) {
      console.error('Failed to load students for recovery:', err)
    } finally {
      setStudentsLoading(false)
    }
  }

  const fetchDashboard = async (id: string) => {
    setLoading(true); setError(null); setData(null)
    setSelectedUserId(id)
    try {
      const result = await fetchWithTimeout(`/recovery/dashboard/${id}`)
      setData(result)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!data || data.weak_topics.length === 0) return
    setHistoryLoading(true)
    const fetchHistory = async () => {
      const hist: TopicHistory = {}
      await Promise.all(data.weak_topics.map(async (wt) => {
        try {
          const res = await fetchWithTimeout(`/recovery/history/${data.user_id}/${encodeURIComponent(wt.topic)}`)
          if (res.history) hist[wt.topic] = res.history
        } catch { /* skip */ }
      }))
      setHistory(hist)
      setHistoryLoading(false)
    }
    fetchHistory()
  }, [data])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (userId.trim()) fetchDashboard(userId.trim())
  }

  const markAllRead = async () => {
    if (!data) return
    try {
      await fetchWithTimeout(`/recovery/notifications/read-all/${data.user_id}`, { method: 'PUT' })
      setData({ ...data, notifications: [], unread_notifications: 0 })
    } catch { /* ignore */ }
  }

  return (
    <div>
      <PageHeader
        icon={<Activity className="w-6 h-6" />}
        title={t('title')}
        description={t('subtitle')}
      />

      <Card className="mb-6">
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          <div className="flex-1">
            <label className="text-small text-foreground-muted block mb-1.5">{t('student_id')}</label>
            <input
              type="text"
              value={userId}
              onChange={e => setUserId(e.target.value)}
              placeholder={t('student_id_placeholder')}
              className="w-full px-4 py-2 border border-border rounded-lg text-body bg-background text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <Button type="submit" variant="primary" loading={loading} disabled={!userId.trim()}>
            <Search className="w-4 h-4" />
            {t('look_up')}
          </Button>
        </form>

        {students.length > 0 && (
          <div className="mt-4">
            <p className="text-small text-foreground-muted mb-2">{t('quick_select')}</p>
            <div className="flex flex-wrap gap-2">
              {students.slice(0, 10).map(s => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => { setUserId(s.id); fetchDashboard(s.id) }}
                  className="px-3 py-1.5 border border-border rounded-lg text-small text-foreground-muted hover:text-foreground hover:bg-background-secondary transition-colors"
                >
                  {s.id.slice(0, 8)}...
                </button>
              ))}
            </div>
          </div>
        )}
      </Card>

      {loading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      )}

      {error && (
        <Card className="flex items-start gap-3 mb-6 bg-red-500/5 border-red-500/20">
          <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-subhead font-medium text-red-400">{t('error_generic')}</p>
            <p className="text-small text-red-400/80 mt-1">{error}</p>
          </div>
        </Card>
      )}

      {data && !loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
            <Card>
              <p className="text-small text-foreground-muted">{t('weak_topics')}</p>
              <p className="text-display text-foreground mt-1">{data.total_weak_topics}</p>
            </Card>
            <Card>
              <p className="text-small text-foreground-muted">{t('active_plans')}</p>
              <p className="text-display text-foreground mt-1">{data.total_active_plans}</p>
            </Card>
            <Card>
              <p className="text-small text-foreground-muted">{t('recommendations')}</p>
              <p className="text-display text-foreground mt-1">{data.recommendations.length}</p>
            </Card>
            <Card>
              <p className="text-small text-foreground-muted">{t('critical_topics')}</p>
              <p className="text-display text-red-400 mt-1">
                {data.weak_topics.filter(w => w.severity === 'critical').length}
              </p>
            </Card>
            <Card>
              <p className="text-small text-foreground-muted">{t('due_reviews')}</p>
              <p className={`text-display mt-1 ${data.total_due_reviews > 0 ? 'text-orange-400' : 'text-foreground'}`}>
                {data.total_due_reviews}
              </p>
            </Card>
            <Card
              onClick={() => setNotificationsExpanded(!notificationsExpanded)}
              className="relative cursor-pointer"
            >
              <p className="text-small text-foreground-muted">{t('notifications')}</p>
              <div className="flex items-center gap-2 mt-1">
                <p className="text-display text-foreground">{data.unread_notifications}</p>
                <Bell className="w-4 h-4 text-yellow-400" />
              </div>
              {data.unread_notifications > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
                  <span className="text-[10px] font-bold text-white">{data.unread_notifications}</span>
                </span>
              )}
            </Card>
          </div>

          {data.weak_topics.length >= 3 && (
            <Card>
              <h2 className="text-heading text-foreground mb-4">{t('mastery_overview')}</h2>
              <MasteryRadarChart
                data={data.weak_topics.map(wt => ({ topic: wt.topic, mastery: wt.average_score }))}
              />
            </Card>
          )}

          {history && Object.keys(history).length >= 2 && (
            <Card>
              <h2 className="text-heading text-foreground mb-4">{t('progress_heatmap')}</h2>
              <TopicHeatmap history={history} />
            </Card>
          )}

          {notificationsExpanded && data.notifications.length > 0 && (
            <Card>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Bell className={`w-5 h-5 ${data.unread_notifications > 0 ? 'text-yellow-400' : 'text-foreground-muted'}`} />
                  <h2 className="text-heading text-foreground">{t('recent_notifications')}</h2>
                </div>
                {data.unread_notifications > 0 && (
                  <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); markAllRead() }}>
                    {t('mark_all_read')}
                  </Button>
                )}
              </div>
              <div className="space-y-2">
                {data.notifications.map((n, i) => {
                  const Icon = notificationIconName(n.event_type)
                  return (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-background-secondary/50">
                      <div className={`p-2 rounded-full ${notificationIconColor(n.event_type)}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-body text-foreground">{n.message}</p>
                        <p className="text-small text-foreground-muted mt-1">
                          {n.topic} · {new Date(n.created_at).toLocaleDateString(locale)}
                          {n.improvement_pct && ` · +${n.improvement_pct.toFixed(0)}%`}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>
          )}

          {data.recommendations.length > 0 && (
            <Card>
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-5 h-5 text-yellow-400" />
                <h2 className="text-heading text-foreground">{t('recommendations')}</h2>
              </div>
              <div className="space-y-2">
                {data.recommendations.map((rec, i) => (
                  <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border-l-4 ${priorityBorder(rec.priority)}`}>
                    <ArrowRight className={`w-4 h-4 mt-0.5 ${
                      rec.priority === 'high' ? 'text-red-400' :
                      rec.priority === 'medium' ? 'text-yellow-400' : 'text-blue-400'
                    }`} />
                    <div>
                      <p className="text-body text-foreground">{rec.message}</p>
                      <p className="text-small text-foreground-muted mt-0.5 capitalize">{rec.type.replace(/_/g, ' ')}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {data.total_due_reviews > 0 && (
            <Card>
              <div className="flex items-center gap-2 mb-4">
                <RotateCcw className="w-5 h-5 text-orange-400" />
                <h2 className="text-heading text-foreground">{t('due_reviews')}</h2>
                <span className="ml-auto text-small text-foreground-muted">{data.total_due_reviews} {data.total_due_reviews !== 1 ? t('topics') : t('topic')} {t('due')}</span>
              </div>
              <div className="space-y-2">
                {data.due_reviews.map((review, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-orange-500/5 border border-orange-500/20">
                    <div className="flex items-center gap-3">
                      <RotateCcw className="w-4 h-4 text-orange-400" />
                      <div>
                        <p className="text-body font-medium text-foreground">{review.topic}</p>
                        <p className="text-small text-foreground-muted">
                          Mastery: {review.mastery_score.toFixed(0)}% · Review #{review.review_count + 1} · {review.days_overdue > 0 ? `${review.days_overdue}d ${t('overdue')}` : t('due_today')}
                        </p>
                      </div>
                    </div>
                    <span className="text-small text-foreground-muted whitespace-nowrap">
                      {review.interval_days}{t('d_interval')}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {data.weak_topics.length > 0 ? (
            <Card>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-heading text-foreground">{t('weak_topics')}</h2>
                <span className="text-small text-foreground-muted">{data.total_weak_topics} {data.total_weak_topics !== 1 ? t('topics') : t('topic')}</span>
              </div>
              <LearningTree topics={data.weak_topics} />
              <div className="space-y-3 mt-4">
                {data.weak_topics.map((wt, i) => (
                  <div key={i} className="p-4 rounded-lg border border-border bg-card">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="text-subhead text-foreground">{wt.topic}</h3>
                        <p className="text-small text-foreground-muted">
                          {wt.unit && `${wt.unit} · `}Grade {wt.grade_level}
                        </p>
                      </div>
                      <Badge variant={severityBadgeVariant(wt.severity)}>
                        {wt.severity}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-3 mt-3">
                      <div>
                        <p className="text-small text-foreground-muted">{t('avg_score')}</p>
                        <p className="text-subhead text-foreground">{wt.average_score.toFixed(0)}%</p>
                      </div>
                      <div>
                        <p className="text-small text-foreground-muted">{t('attempts')}</p>
                        <p className="text-subhead text-foreground">{wt.attempt_count}</p>
                      </div>
                      <div>
                        <p className="text-small text-foreground-muted">{t('confidence')}</p>
                        <p className="text-subhead text-foreground">{(wt.confidence * 100).toFixed(0)}%</p>
                      </div>
                    </div>
                    {wt.misconceptions.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-border/50">
                        <p className="text-small font-medium text-foreground-muted mb-2">{t('misconceptions')}</p>
                        {wt.misconceptions.map((mc, j) => (
                          <div key={j} className="flex items-center gap-2 text-small text-foreground-muted mb-1">
                            <AlertTriangle className="w-3 h-3 text-yellow-400" />
                            <span>{mc.pattern_type}: {mc.description}</span>
                            <span className="text-foreground-muted/60">({mc.frequency}x)</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {history[wt.topic] && history[wt.topic].length >= 2 && (
                      <div className="mt-3 pt-3 border-t border-border/50">
                        <SimpleMiniChart points={history[wt.topic]} topic={wt.topic} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <Card className="text-center py-8">
              <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-3" />
              <p className="text-foreground-muted text-subhead font-medium">{t('no_weak_topics')}</p>
              <p className="text-small text-foreground-muted/60 mt-1">{t('no_weak_topics_subtitle')}</p>
            </Card>
          )}

          {data.active_plans.length > 0 ? (
            <Card>
              <div className="flex items-center gap-2 mb-4">
                <ClipboardList className="w-5 h-5 text-primary" />
                <h2 className="text-heading text-foreground">{t('active_plans')}</h2>
              </div>
              <div className="space-y-4">
                {data.active_plans.map(plan => (
                  <div key={plan.id} className="border border-border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-subhead text-foreground">{plan.topic}</h3>
                        <p className="text-small text-foreground-muted">
                          {plan.completed_tasks}/{plan.total_tasks} {t('tasks')}
                        </p>
                      </div>
                      <span className="text-subhead text-foreground">{plan.progress_pct}%</span>
                    </div>
                    <div className="w-full bg-background-secondary rounded-full h-2 mb-3 overflow-hidden">
                      <div className="bg-primary rounded-full h-2 transition-all" style={{ width: `${plan.progress_pct}%` }} />
                    </div>
                    <div className="space-y-2">
                      {plan.tasks.map(task => {
                        const TaskIcon = taskTypeIcon(task.task_type)
                        return (
                          <div key={task.id} className={`flex items-center gap-3 p-2 rounded-lg text-body ${
                            task.is_completed ? 'bg-green-500/5' : 'bg-background-secondary/50'
                          }`}>
                            {task.is_completed ? (
                              <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />
                            ) : (
                              <Clock className="w-4 h-4 text-yellow-400 shrink-0" />
                            )}
                            <div className="flex-1 min-w-0">
                              <p className={`truncate ${task.is_completed ? 'text-green-400 line-through opacity-60' : 'text-foreground'}`}>
                                {task.title}
                              </p>
                              <p className="text-small text-foreground-muted capitalize">{task.task_type.replace(/_/g, ' ')}</p>
                            </div>
                            {task.is_completed && (
                              <span className="text-small text-green-400/60">+{task.xp_awarded} XP</span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            data.weak_topics.length > 0 && (
              <Card className="text-center py-8">
                <ClipboardList className="w-12 h-12 text-border mx-auto mb-3" />
                <p className="text-foreground-muted text-subhead font-medium">{t('no_plans')}</p>
                <p className="text-small text-foreground-muted/60 mt-1">{t('no_plans_instruction')}</p>
              </Card>
            )
          )}
        </div>
      )}

      {!data && !loading && !error && (
        <div className="text-center py-16">
          <Search className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted text-subhead font-medium">{t('enter_id_hint')}</p>
          <p className="text-small text-foreground-muted/60 mt-1">{t('enter_id_subtitle')}</p>
        </div>
      )}
    </div>
  )
}
