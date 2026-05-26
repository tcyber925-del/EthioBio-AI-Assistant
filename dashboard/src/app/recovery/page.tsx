'use client'

import { useEffect, useState } from 'react'
import { ClipboardList, AlertTriangle, Loader2, Search, CheckCircle2, Clock, BookOpen, Lightbulb, ArrowRight, Target, Brain, TrendingUp, RotateCcw, Bell, PartyPopper, Sparkles } from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'
import { CardSkeleton } from '@/components/Skeleton'
import { MasteryRadarChart } from '@/components/recovery/MasteryRadarChart'
import { ProgressTrendGraph } from '@/components/recovery/ProgressTrendGraph'

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

export default function RecoveryPage() {
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

  useEffect(() => {
    fetchWithTimeout('/api/admin/dashboard')
      .then(d => setStudents(d.recent_users || []))
      .catch(() => {})
      .finally(() => setStudentsLoading(false))
  }, [])

  const fetchDashboard = async (id: string) => {
    setLoading(true)
    setError(null)
    setData(null)
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

  const notificationIcon = (eventType: string) => {
    switch (eventType) {
      case 'mastery_improvement': return TrendingUp
      case 'severity_upgrade': return PartyPopper
      case 'plan_completed': return Sparkles
      default: return Bell
    }
  }

  const notificationColor = (eventType: string) => {
    switch (eventType) {
      case 'mastery_improvement': return 'text-green-400 bg-green-500/10'
      case 'severity_upgrade': return 'text-purple-400 bg-purple-500/10'
      case 'plan_completed': return 'text-blue-400 bg-blue-500/10'
      default: return 'text-yellow-400 bg-yellow-500/10'
    }
  }

  const severityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-400 bg-red-500/10 border-red-500/20'
      case 'moderate': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20'
      case 'mild': return 'text-blue-400 bg-blue-500/10 border-blue-500/20'
      default: return 'text-green-400 bg-green-500/10 border-green-500/20'
    }
  }

  const priorityBg = (priority: string) => {
    switch (priority) {
      case 'high': return 'border-l-red-500 bg-red-500/5'
      case 'medium': return 'border-l-yellow-500 bg-yellow-500/5'
      default: return 'border-l-blue-500 bg-blue-500/5'
    }
  }

  const taskTypeIcon = (type: string) => {
    switch (type) {
      case 'review_notes': return BookOpen
      case 'guided_quiz': return Target
      case 'diagram_exercise': return Brain
      default: return ClipboardList
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Recovery Dashboard</h1>
          <p className="text-sm text-foreground-muted mt-1">
            Track weak topics, active recovery plans, and personalized recommendations
          </p>
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border p-5 mb-6">
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          <div className="flex-1">
            <label className="text-xs text-foreground-muted block mb-1.5">Student ID</label>
            <input
              type="text"
              value={userId}
              onChange={e => setUserId(e.target.value)}
              placeholder="Enter student UUID..."
              className="w-full px-4 py-2 border border-border rounded-lg text-sm bg-background text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !userId.trim()}
            className="px-6 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
          >
            {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Loading...</> : <><Search className="w-4 h-4" /> Look up</>}
          </button>
        </form>

        {students.length > 0 && (
          <div className="mt-4">
            <p className="text-xs text-foreground-muted mb-2">Quick select:</p>
            <div className="flex flex-wrap gap-2">
              {students.slice(0, 10).map(s => (
                <button
                  key={s.id}
                  onClick={() => { setUserId(s.id); fetchDashboard(s.id) }}
                  className="px-3 py-1.5 border border-border rounded-lg text-xs text-foreground-muted hover:text-foreground hover:bg-background-secondary transition-colors"
                >
                  {s.id.slice(0, 8)}...
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {loading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-5 flex items-start gap-3 mb-6">
          <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">Error</p>
            <p className="text-sm text-red-400/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      {data && !loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-card rounded-xl border border-border p-5">
              <p className="text-sm text-foreground-muted">Weak Topics</p>
              <p className="text-2xl font-bold text-foreground mt-1">{data.total_weak_topics}</p>
            </div>
            <div className="bg-card rounded-xl border border-border p-5">
              <p className="text-sm text-foreground-muted">Active Plans</p>
              <p className="text-2xl font-bold text-foreground mt-1">{data.total_active_plans}</p>
            </div>
            <div className="bg-card rounded-xl border border-border p-5">
              <p className="text-sm text-foreground-muted">Recommendations</p>
              <p className="text-2xl font-bold text-foreground mt-1">{data.recommendations.length}</p>
            </div>
            <div className="bg-card rounded-xl border border-border p-5">
              <p className="text-sm text-foreground-muted">Critical Topics</p>
              <p className="text-2xl font-bold text-red-400 mt-1">
                {data.weak_topics.filter(w => w.severity === 'critical').length}
              </p>
            </div>
            <div className="bg-card rounded-xl border border-border p-5">
              <p className="text-sm text-foreground-muted">Due for Review</p>
              <p className={`text-2xl font-bold mt-1 ${data.total_due_reviews > 0 ? 'text-orange-400' : 'text-foreground'}`}>
                {data.total_due_reviews}
              </p>
            </div>
            <div
              className="bg-card rounded-xl border border-border p-5 cursor-pointer hover:bg-background-secondary/50 transition-colors relative"
              onClick={() => setNotificationsExpanded(!notificationsExpanded)}
            >
              <p className="text-sm text-foreground-muted">Notifications</p>
              <div className="flex items-center gap-2 mt-1">
                <p className="text-2xl font-bold text-foreground">{data.unread_notifications}</p>
                <Bell className="w-4 h-4 text-yellow-400" />
              </div>
              {data.unread_notifications > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
                  <span className="text-[10px] font-bold text-white">{data.unread_notifications}</span>
                </span>
              )}
            </div>
          </div>

          {data.weak_topics.length >= 3 && (
            <div className="bg-card rounded-xl border border-border p-5">
              <h2 className="text-lg font-semibold text-foreground mb-4">Mastery Overview</h2>
              <MasteryRadarChart
                data={data.weak_topics.map(wt => ({
                  topic: wt.topic,
                  mastery: wt.average_score,
                }))}
              />
            </div>
          )}

          {notificationsExpanded && data.notifications.length > 0 && (
            <div className="bg-card rounded-xl border border-border p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Bell className={`w-5 h-5 ${data.unread_notifications > 0 ? 'text-yellow-400' : 'text-foreground-muted'}`} />
                  <h2 className="text-lg font-semibold text-foreground">Recent Notifications</h2>
                </div>
                {data.unread_notifications > 0 && (
                  <button
                    onClick={(e) => { e.stopPropagation(); markAllRead() }}
                    className="text-xs text-primary hover:text-primary-hover transition-colors"
                  >
                    Mark all as read
                  </button>
                )}
              </div>
              <div className="space-y-2">
                {data.notifications.map((n, i) => {
                  const Icon = notificationIcon(n.event_type)
                  return (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-background-secondary/50">
                      <div className={`p-2 rounded-full ${notificationColor(n.event_type)}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-foreground">{n.message}</p>
                        <p className="text-xs text-foreground-muted mt-1">
                          {n.topic} · {new Date(n.created_at).toLocaleDateString()}
                          {n.improvement_pct && ` · +${n.improvement_pct.toFixed(0)}%`}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {data.recommendations.length > 0 && (
            <div className="bg-card rounded-xl border border-border p-5">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-5 h-5 text-yellow-400" />
                <h2 className="text-lg font-semibold text-foreground">Recommendations</h2>
              </div>
              <div className="space-y-2">
                {data.recommendations.map((rec, i) => (
                  <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border-l-4 ${priorityBg(rec.priority)}`}>
                    <ArrowRight className={`w-4 h-4 mt-0.5 ${
                      rec.priority === 'high' ? 'text-red-400' :
                      rec.priority === 'medium' ? 'text-yellow-400' : 'text-blue-400'
                    }`} />
                    <div>
                      <p className="text-sm text-foreground">{rec.message}</p>
                      <p className="text-xs text-foreground-muted mt-0.5 capitalize">{rec.type.replace(/_/g, ' ')}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.total_due_reviews > 0 && (
            <div className="bg-card rounded-xl border border-border p-5">
              <div className="flex items-center gap-2 mb-4">
                <RotateCcw className="w-5 h-5 text-orange-400" />
                <h2 className="text-lg font-semibold text-foreground">Due for Review</h2>
                <span className="ml-auto text-sm text-foreground-muted">{data.total_due_reviews} topic{data.total_due_reviews !== 1 ? 's' : ''} due</span>
              </div>
              <div className="space-y-2">
                {data.due_reviews.map((review, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-orange-500/5 border border-orange-500/20">
                    <div className="flex items-center gap-3">
                      <RotateCcw className="w-4 h-4 text-orange-400" />
                      <div>
                        <p className="text-sm font-medium text-foreground">{review.topic}</p>
                        <p className="text-xs text-foreground-muted">
                          Mastery: {review.mastery_score.toFixed(0)}% · Review #{review.review_count + 1} · {review.days_overdue > 0 ? `${review.days_overdue}d overdue` : 'Due today'}
                        </p>
                      </div>
                    </div>
                    <span className="text-xs text-foreground-muted whitespace-nowrap">
                      {review.interval_days}d interval
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.weak_topics.length > 0 ? (
            <div className="bg-card rounded-xl border border-border p-5">
              <h2 className="text-lg font-semibold text-foreground mb-4">Weak Topics</h2>
              <div className="space-y-3">
                {data.weak_topics.map((wt, i) => (
                  <div key={i} className={`p-4 rounded-lg border ${severityColor(wt.severity)}`}>
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-medium text-foreground">{wt.topic}</h3>
                        <p className="text-xs text-foreground-muted">
                          {wt.unit && `${wt.unit} · `}Grade {wt.grade_level}
                        </p>
                      </div>
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium capitalize border ${severityColor(wt.severity)}`}>
                        {wt.severity}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-3 mt-3">
                      <div>
                        <p className="text-xs text-foreground-muted">Avg Score</p>
                        <p className="text-sm font-semibold text-foreground">{wt.average_score.toFixed(0)}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-foreground-muted">Attempts</p>
                        <p className="text-sm font-semibold text-foreground">{wt.attempt_count}</p>
                      </div>
                      <div>
                        <p className="text-xs text-foreground-muted">Confidence</p>
                        <p className="text-sm font-semibold text-foreground">{(wt.confidence * 100).toFixed(0)}%</p>
                      </div>
                    </div>
                    {wt.misconceptions.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-border/50">
                        <p className="text-xs font-medium text-foreground-muted mb-2">Misconceptions:</p>
                        {wt.misconceptions.map((mc, j) => (
                          <div key={j} className="flex items-center gap-2 text-xs text-foreground-muted mb-1">
                            <AlertTriangle className="w-3 h-3 text-yellow-400" />
                            <span>{mc.pattern_type}: {mc.description}</span>
                            <span className="text-foreground-muted/60">({mc.frequency}x)</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {history[wt.topic] && (
                      <div className="mt-3 pt-3 border-t border-border/50">
                        <ProgressTrendGraph data={history[wt.topic]} topic={wt.topic} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-card rounded-xl border border-border p-8 text-center">
              <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-3" />
              <p className="text-foreground-muted font-medium">No weak topics found</p>
              <p className="text-sm text-foreground-muted/60 mt-1">Student is performing well across all topics</p>
            </div>
          )}

          {data.active_plans.length > 0 ? (
            <div className="bg-card rounded-xl border border-border p-5">
              <div className="flex items-center gap-2 mb-4">
                <ClipboardList className="w-5 h-5 text-primary" />
                <h2 className="text-lg font-semibold text-foreground">Active Recovery Plans</h2>
              </div>
              <div className="space-y-4">
                {data.active_plans.map(plan => {
                  const TaskIcon = taskTypeIcon
                  return (
                    <div key={plan.id} className="border border-border rounded-lg p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="font-medium text-foreground">{plan.topic}</h3>
                          <p className="text-xs text-foreground-muted">
                            {plan.completed_tasks}/{plan.total_tasks} tasks completed
                          </p>
                        </div>
                        <span className="text-sm font-semibold text-foreground">{plan.progress_pct}%</span>
                      </div>
                      <div className="w-full bg-background-secondary rounded-full h-2 mb-3">
                        <div
                          className="bg-primary rounded-full h-2 transition-all"
                          style={{ width: `${plan.progress_pct}%` }}
                        />
                      </div>
                      <div className="space-y-2">
                        {plan.tasks.map(task => (
                          <div key={task.id} className={`flex items-center gap-3 p-2 rounded-lg text-sm ${
                            task.is_completed ? 'bg-green-500/5' : 'bg-background-secondary/50'
                          }`}>
                            {task.is_completed ? (
                              <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
                            ) : (
                              <Clock className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                            )}
                            <div className="flex-1 min-w-0">
                              <p className={`truncate ${task.is_completed ? 'text-green-400 line-through opacity-60' : 'text-foreground'}`}>
                                {task.title}
                              </p>
                              <p className="text-xs text-foreground-muted capitalize">{task.task_type.replace(/_/g, ' ')}</p>
                            </div>
                            {task.is_completed && (
                              <span className="text-xs text-green-400/60">+{task.xp_awarded} XP</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : (
            data.weak_topics.length > 0 && (
              <div className="bg-card rounded-xl border border-border p-8 text-center">
                <ClipboardList className="w-12 h-12 text-border mx-auto mb-3" />
                <p className="text-foreground-muted font-medium">No active recovery plans</p>
                <p className="text-sm text-foreground-muted/60 mt-1">
                  Generate a recovery plan using the auto-generate endpoint to start tracking progress
                </p>
              </div>
            )
          )}
        </div>
      )}

      {!data && !loading && !error && (
        <div className="text-center py-16">
          <Search className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">Enter a student ID to get started</p>
          <p className="text-sm text-foreground-muted/60 mt-1">
            Type a UUID or select a student from the quick list above
          </p>
        </div>
      )}
    </div>
  )
}