'use client'

import { useEffect, useState } from 'react'
import { useLocale, useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'

export const dynamic = 'force-dynamic'

interface DashboardData {
  users: number
  teachers: number
  students: number
  quizzes: number
  lesson_plans: number
  quiz_attempts: number
  recent_users: Array<{ id: string; role: string; grade_level: number | null; created_at: string }>
  recent_logs: Array<{ id: string; request_type: string; model_used: string; success: boolean; latency_ms: number | null; created_at: string }>
}

export default function AdminDashboardPage() {
  const locale = useLocale()
  const ta = useTranslations('admin.dashboard')
  const tc = useTranslations('common')
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWithAuth('/api/admin/dashboard')
      .then(res => res.json())
      .then(setData)
      .catch(err => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  if (error) return <p className="text-red-400">{tc('error')}: {error}</p>
  if (!data) return <p className="text-foreground-muted text-body">{tc('loading')}</p>

  return (
    <div>
      <h1 className="text-heading text-foreground mb-6">{ta('overview')}</h1>
      <div className="grid grid-cols-5 gap-4 mb-8">
        {[
          { label: ta('users'), value: data.users, color: 'bg-blue-500/10 text-blue-400 border border-blue-500/20' },
          { label: ta('total_teachers'), value: data.teachers, color: 'bg-green-500/10 text-green-400 border border-green-500/20' },
          { label: ta('total_students'), value: data.students, color: 'bg-purple-500/10 text-purple-400 border border-purple-500/20' },
          { label: ta('quizzes'), value: data.quizzes, color: 'bg-amber-500/10 text-amber-400 border border-amber-500/20' },
          { label: ta('lessons'), value: data.lesson_plans, color: 'bg-rose-500/10 text-rose-400 border border-rose-500/20' },
        ].map(({ label, value, color }) => (
          <div key={label} className={`p-4 rounded-xl ${color}`}>
            <div className="text-display font-bold">{value}</div>
            <div className="text-small text-foreground-muted">{label}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h2 className="text-heading text-foreground mb-4">{ta('recent_users')}</h2>
          <table className="w-full text-body">
            <thead>
              <tr className="bg-background-secondary">
                <th className="p-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{ta('col_id')}</th>
                <th className="p-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{ta('col_role')}</th>
                <th className="p-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{ta('col_grade')}</th>
                <th className="p-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{ta('col_created')}</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_users.map(u => (
                <tr key={u.id} className="border-t border-border">
                  <td className="p-3 text-mono text-foreground-muted">{u.id.slice(0, 8)}...</td>
                  <td className="p-3 capitalize text-foreground">{u.role}</td>
                  <td className="p-3 text-foreground-muted">{u.grade_level ?? '-'}</td>
                  <td className="p-3 text-foreground-muted">{new Date(u.created_at).toLocaleDateString(locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card>
          <h2 className="text-heading text-foreground mb-4">{ta('recent_model_logs')}</h2>
          <table className="w-full text-body">
            <thead>
              <tr className="bg-background-secondary">
                <th className="p-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{ta('col_type')}</th>
                <th className="p-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{ta('col_model')}</th>
                <th className="p-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{ta('col_status')}</th>
                <th className="p-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{ta('col_latency')}</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_logs.map(log => (
                <tr key={log.id} className="border-t border-border">
                  <td className="p-3 text-foreground">{log.request_type}</td>
                  <td className="p-3 text-mono text-foreground-muted">{log.model_used}</td>
                  <td className="p-3">{log.success ? <span className="text-green-400">✓</span> : <span className="text-red-400">✗</span>}</td>
                  <td className="p-3 text-foreground-muted">{log.latency_ms != null ? `${(log.latency_ms / 1000).toFixed(1)}s` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  )
}
