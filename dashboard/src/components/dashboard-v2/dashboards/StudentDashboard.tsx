'use client'

import { useEffect, useState } from 'react'
import { BookOpen, AlertTriangle, RefreshCw, Lock } from 'lucide-react'
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

function deriveInsights(data: StudentData): string[] {
  const insights: string[] = []
  if (data.weak_topics.length > 0) {
    const w = data.weak_topics[0]
    insights.push(`Focus on **${w.topic}** — your performance is at ${w.average_score.toFixed(0)}%. Regular review will strengthen this area.`)
  }
  if (data.due_reviews.length > 0) {
    insights.push(`You have **${data.due_reviews.length} review${data.due_reviews.length > 1 ? 's' : ''}** due. Spaced repetition keeps knowledge fresh.`)
  }
  if (data.gamification.longest_streak > 0 && data.gamification.current_streak < data.gamification.longest_streak) {
    insights.push(`Your best streak is **${data.gamification.longest_streak} days**. Can you beat it? Consistency is key to mastery.`)
  }
  if (data.gamification.current_streak >= 3) {
    insights.push(`**${data.gamification.current_streak}-day streak!** You are building strong learning habits. Keep it going.`)
  }
  return insights
}

function buildMilestones(data: StudentData) {
  const m = [
    { label: 'Complete first review', completed: data.gamification.total_xp > 0 },
    { label: '3-day streak', completed: data.gamification.current_streak >= 3 },
    { label: 'Level 5', completed: data.gamification.level >= 5 },
  ]
  if (data.weak_topics.length > 0) {
    m.push({ label: `Strengthen ${data.weak_topics[0].topic}`, completed: false })
  }
  return m
}

function userName(data: StudentData): string {
  return data.user.email ? data.user.email.split('@')[0] : 'there'
}

export function StudentDashboard() {
  const [data, setData] = useState<StudentData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true); setError(null)
    try {
      const d = await fetchWithAuth('/api/student/dashboard')
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
          <p className="mt-3 text-sm text-v2-text-secondary">Loading your dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center max-w-sm">
          <AlertTriangle className="w-10 h-10 text-v2-error mx-auto mb-3" />
          <p className="text-sm font-medium text-v2-error">Something went wrong</p>
          <p className="text-xs text-v2-text-secondary mt-1 mb-4">{error}</p>
          <button onClick={retry} className="inline-flex items-center gap-2 px-4 h-9 rounded-xl bg-v2-accent text-white text-sm font-medium hover:bg-v2-accent-hover transition-colors">
            <RefreshCw className="w-4 h-4" /> Retry
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
  const insights = deriveInsights(data)
  const milestones = buildMilestones(data)

  return (
    <>
      <HeroSection
        title={`Welcome back, ${userName(data)}`}
        subtitle={continueTopic
          ? `Focus on ${continueTopic.topic} — your lowest score is ${continueTopic.average_score.toFixed(0)}%`
          : `You're at ${readiness.overall_readiness.toFixed(0)}% overall readiness`
        }
        action={continueTopic ? { label: 'Review ' + continueTopic.topic, href: '/v2/lessons' } : undefined}
        secondary={readiness.overall_readiness >= 80 ? '🌟 Strong readiness'
          : readiness.overall_readiness >= 50 ? '📈 Steady progress'
          : '🎯 Focused improvement needed'}
      />

      {continueTopic && (
        <div className="mb-6">
          <div className="bg-v2-surface rounded-[20px] border border-v2-accent/30 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)] p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-xl bg-v2-accent-muted text-v2-accent">
                  <BookOpen className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs font-medium text-v2-text-secondary uppercase tracking-wider">Continue Learning</p>
                  <h3 className="mt-1 text-xl font-semibold text-v2-text-primary">{continueTopic.topic}</h3>
                  <p className="mt-1 text-sm text-v2-text-secondary">
                    {continueTopic.misconceptions.length > 0
                      ? `Address ${continueTopic.misconceptions[0]}`
                      : `Review — ${continueTopic.average_score.toFixed(0)}% mastery`
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
          { label: 'Readiness', value: `${readiness.overall_readiness.toFixed(0)}%`, accent: true },
          { label: 'XP Total', value: gamification.total_xp.toLocaleString() },
          { label: 'Streak', value: `${gamification.current_streak} days` },
          { label: 'Level', value: gamification.level.toString() },
        ]} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 space-y-6">
          <LearningProgress title="Weekly Progress" percent={readiness.overall_readiness} milestones={milestones} />

          {sortedTopics.length > 0 && (
            <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)]">
              <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Topic Mastery</h2>
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

          {weak_topics.length > 0 && (
            <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)]">
              <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Areas to Improve ({weak_topics.length})</h2>
              <div className="space-y-2">
                {weak_topics.slice(0, 5).map(wt => (
                  <div key={wt.topic} className="p-3 rounded-xl bg-v2-bg">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-sm font-medium text-v2-text-primary">{wt.topic}</span>
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${wt.severity === 'critical' ? 'bg-v2-error/10 text-v2-error' : wt.severity === 'moderate' ? 'bg-v2-warning/10 text-v2-warning' : 'bg-v2-accent-muted text-v2-accent'}`}>{wt.severity}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-v2-text-secondary">
                      <span>Score: {wt.average_score.toFixed(0)}%</span>
                      <span>Attempts: {wt.attempt_count}</span>
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
            <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)]">
              <ActivityTimeline items={recent_activity} />
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)]">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-v2-accent-muted text-v2-accent"><BookOpen className="w-5 h-5" /></div>
              <div>
                <p className="text-xs text-v2-text-secondary">Achievements</p>
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
