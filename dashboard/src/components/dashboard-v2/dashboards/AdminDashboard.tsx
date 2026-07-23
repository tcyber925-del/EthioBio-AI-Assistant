'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw, CheckCircle } from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { HeroSection, InsightCard, MetricStrip, AIInsightPanel } from '@/components/dashboard-v2'

interface DashboardData {
  users: number; teachers: number; students: number
  quizzes: number; lesson_plans: number; quiz_attempts: number
  recent_users: Array<{ id: string; role: string; grade_level: number | null; created_at: string }>
  recent_logs: Array<{
    id: string; request_type: string; model_used: string
    success: boolean; latency_ms: number | null; created_at: string
  }>
}

function deriveAdminInsights(data: DashboardData): string[] {
  const insights: string[] = []
  const totalActive = data.users
  insights.push(`${totalActive.toLocaleString()} total users on the platform. Student-to-teacher ratio: ${data.students > 0 ? (data.students / Math.max(data.teachers, 1)).toFixed(1) : 'N/A'}:1.`)
  if (data.quiz_attempts > 0) insights.push(`${data.quiz_attempts.toLocaleString()} quiz attempts logged. Assessment engagement is ${data.quiz_attempts > 500 ? 'strong' : 'growing'}.`)
  if (data.recent_logs.length > 0) {
    const failed = data.recent_logs.filter(l => !l.success).length
    if (failed > 3) insights.push(`⚠️ ${failed} failed requests in recent logs. AI infrastructure may need attention.`)
  }
  const recentUserCount = data.recent_users.length
  if (recentUserCount > 0) insights.push(`${recentUserCount} new user${recentUserCount > 1 ? 's' : ''} registered recently. Platform adoption is ${recentUserCount > 5 ? 'accelerating' : 'steady'}.`)
  return insights
}

export function AdminDashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true); setError(null)
    try {
      const response = await fetchWithAuth('/api/admin/dashboard')
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
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    )
  }

  if (!data) return null

  const { users, teachers, students, quizzes, lesson_plans, recent_users, recent_logs } = data
  const successRate = recent_logs.length > 0
    ? ((recent_logs.filter(l => l.success).length / recent_logs.length) * 100).toFixed(0)
    : '0'
  const insights = deriveAdminInsights(data)

  return (
    <>
      <HeroSection
        title="Platform Overview"
        subtitle={`${students.toLocaleString()} active learners · ${teachers} teachers · ${users} users`}
        secondary={<span><CheckCircle className="inline h-4 w-4 mr-1.5 text-v2-accent" /> Healthy system status</span>}
      />

      <div className="mb-6">
        <MetricStrip metrics={[
          { label: 'Students', value: students.toLocaleString(), accent: true },
          { label: 'Teachers', value: teachers.toString() },
          { label: 'Quizzes', value: quizzes.toString() },
          { label: 'Lessons', value: lesson_plans.toString() },
        ]} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <InsightCard title="Platform Users" value={users.toLocaleString()} context="Total registered accounts" index={0} />
        <InsightCard title="AI Success Rate" value={`${successRate}%`} trend={{ direction: Number(successRate) >= 80 ? 'up' : 'down', label: `${successRate}% success` }} context="AI response success rate" index={1} />
        <InsightCard title="New Users" value={recent_users.length.toString()} context="Recent registrations" index={2} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Recent Users */}
          <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
            <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Recent Users</h2>
            {recent_users.length > 0 ? (
              <div className="space-y-2">
                {recent_users.slice(0, 10).map(u => (
                  <div key={u.id} className="flex items-center justify-between py-2 border-b border-v2-border/50 last:border-0">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-mono text-v2-text-secondary">{u.id.slice(0, 8)}...</span>
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-v2-accent-muted text-v2-accent">{u.role}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-v2-text-secondary">
                      {u.grade_level && <span>Grade {u.grade_level}</span>}
                      <span>{new Date(u.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-v2-text-secondary">No recent user registrations.</p>
            )}
          </div>

          {/* System Events / AI Logs */}
          <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
            <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Recent System Activity</h2>
            {recent_logs.length > 0 ? (
              <div className="space-y-2">
                {recent_logs.slice(0, 10).map(log => (
                  <div key={log.id} className="flex items-center gap-3 py-2 border-b border-v2-border/50 last:border-0">
                    <div className={`w-2 h-2 rounded-full shrink-0 ${log.success ? 'bg-v2-success' : 'bg-v2-error'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-v2-text-primary truncate">{log.request_type}</p>
                      <p className="text-xs text-v2-text-secondary">{log.model_used}</p>
                    </div>
                    <span className="text-xs font-mono text-v2-text-secondary">
                      {log.latency_ms != null ? `${(log.latency_ms / 1000).toFixed(1)}s` : '-'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-v2-text-secondary">No recent system activity.</p>
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
