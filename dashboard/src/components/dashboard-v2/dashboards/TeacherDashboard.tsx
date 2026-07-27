'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw, Users, BookOpen, FileQuestion, BarChart3 } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserRole } from '@/lib/auth'
import { HeroSection, InsightCard, MetricStrip, AIInsightPanel } from '@/components/dashboard-v2'

interface DashboardData {
  users: number; teachers: number; students: number
  quizzes: number; lesson_plans: number; quiz_attempts: number
  recent_logs: Array<{
    id: string; request_type: string; model_used: string
    success: boolean; latency_ms: number; created_at: string
  }>
}

type TFn = (key: string, values?: Record<string, string | number>) => string

function deriveInsights(data: DashboardData, t: TFn): string[] {
  const insights: string[] = []
  const activeStudents = data.students
  if (activeStudents > 0) insights.push(t('insight_students', { count: activeStudents }))
  if (data.quiz_attempts > 100) insights.push(t('insight_engagement', { count: data.quiz_attempts }))
  if (data.recent_logs.length > 0) {
    const failed = data.recent_logs.filter(l => !l.success).length
    if (failed > 0) insights.push(t('insight_failed', { count: failed }))
    const avgLatency = data.recent_logs.reduce((s, l) => s + l.latency_ms, 0) / data.recent_logs.length
    insights.push(t(avgLatency < 2000 ? 'insight_latency_healthy' : 'insight_latency_degraded', { seconds: (avgLatency / 1000).toFixed(1) }))
  }
  return insights
}

export function TeacherDashboard() {
  const t = useTranslations('v2.teacher')
  const tc = useTranslations('common')
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    const role = getUserRole()
    const endpoint = role === 'admin' ? '/api/admin/dashboard' : '/api/teacher/dashboard'
    setLoading(true); setError(null)
    try {
      const response = await fetchWithAuth(endpoint)
      const d = await response.json()
      setData(d)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  if (loading && !data) {
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
          <button onClick={fetchData} className="inline-flex items-center gap-2 px-4 h-9 rounded-xl bg-v2-accent text-v2-inverted text-sm font-medium hover:bg-white transition-colors">
            <RefreshCw className="w-4 h-4" /> {tc('retry')}
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  const { students, quizzes, lesson_plans, quiz_attempts, recent_logs } = data
  const successRate = recent_logs.length > 0
    ? ((recent_logs.filter(l => l.success).length / recent_logs.length) * 100).toFixed(0)
    : '0'
  const avgLatency = recent_logs.length > 0
    ? (recent_logs.reduce((s, l) => s + l.latency_ms, 0) / recent_logs.length / 1000).toFixed(1)
    : '0'
  const insights = deriveInsights(data, t)
  const activeToday = students

  return (
    <>
      <HeroSection
        title={t('title')}
        subtitle={t('subtitle_active', { count: activeToday })}
        secondary={t('secondary_counts', { quizzes, lessons: lesson_plans, attempts: quiz_attempts })}
      />

      <div className="mb-6">
        <MetricStrip metrics={[
          { label: t('metric_students'), value: students.toLocaleString(), accent: true },
          { label: t('metric_quizzes'), value: quizzes.toLocaleString() },
          { label: t('metric_lessons'), value: lesson_plans.toLocaleString() },
          { label: t('metric_attempts'), value: quiz_attempts.toLocaleString() },
        ]} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <InsightCard title={t('engagement_title')} value={t('engagement_value', { count: Number((quiz_attempts / Math.max(students, 1)).toFixed(1)) })} context={t('engagement_context')} index={0} />
        <InsightCard title={t('success_title')} value={`${successRate}%`} trend={{ direction: Number(successRate) >= 80 ? 'up' : 'down', label: t('success_trend', { pct: successRate }) }} context={t('success_context')} index={1} />
        <InsightCard title={t('latency_title')} value={`${avgLatency}s`} trend={{ direction: Number(avgLatency) <= 2 ? 'up' : 'down', label: t(Number(avgLatency) <= 2 ? 'latency_good' : 'latency_degraded') }} context={t('latency_context')} index={2} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
            <h2 className="text-lg font-semibold text-v2-text-primary mb-4">{t('recent_activity')}</h2>
            {recent_logs.length > 0 ? (
              <div className="space-y-2">
                {recent_logs.slice(0, 10).map(log => (
                  <div key={log.id} className="flex items-center gap-3 py-2 border-b border-v2-border/50 last:border-0">
                    <div className={`p-1.5 rounded-lg ${log.success ? 'bg-v2-success/10 text-v2-success' : 'bg-v2-error/10 text-v2-error'}`}>
                      <BarChart3 className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-v2-text-primary truncate">{log.request_type}</p>
                      <p className="text-xs text-v2-text-secondary">{log.model_used} · {(log.latency_ms / 1000).toFixed(1)}s</p>
                    </div>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${log.success ? 'bg-v2-success/10 text-v2-success' : 'bg-v2-error/10 text-v2-error'}`}>
                      {t(log.success ? 'status_ok' : 'status_fail')}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-v2-text-secondary">{t('no_activity')}</p>
            )}
          </div>
        </div>
        <div className="space-y-6">
          <AIInsightPanel insights={insights} />
        </div>
      </div>
    </>
  )
}
