'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

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
  const ta = useTranslations('admin.dashboard')
  const tc = useTranslations('common')
  const [data, setData] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWithAuth('/api/admin/dashboard')
      .then(setData)
      .catch(err => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  if (error) return <p className="text-red-600">{tc('error')}: {error}</p>
  if (!data) return <p className="text-gray-500">{tc('loading')}</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{ta('overview')}</h1>
      <div className="grid grid-cols-5 gap-4 mb-8">
        {[
          { label: ta('users'), value: data.users, color: 'bg-blue-50 text-blue-700' },
          { label: ta('total_teachers'), value: data.teachers, color: 'bg-green-50 text-green-700' },
          { label: ta('total_students'), value: data.students, color: 'bg-purple-50 text-purple-700' },
          { label: ta('quizzes'), value: data.quizzes, color: 'bg-amber-50 text-amber-700' },
          { label: ta('lessons'), value: data.lesson_plans, color: 'bg-rose-50 text-rose-700' },
        ].map(({ label, value, color }) => (
          <div key={label} className={`p-4 rounded-lg ${color}`}>
            <div className="text-2xl font-bold">{value}</div>
            <div className="text-sm">{label}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-6">
        <section>
          <h2 className="text-lg font-semibold mb-3">{ta('recent_users')}</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="p-2 text-left">{ta('col_id')}</th>
                <th className="p-2 text-left">{ta('col_role')}</th>
                <th className="p-2 text-left">{ta('col_grade')}</th>
                <th className="p-2 text-left">{ta('col_created')}</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_users.map(u => (
                <tr key={u.id} className="border-t">
                  <td className="p-2 font-mono text-xs">{u.id.slice(0, 8)}...</td>
                  <td className="p-2 capitalize">{u.role}</td>
                  <td className="p-2">{u.grade_level ?? '-'}</td>
                  <td className="p-2 text-gray-500">{new Date(u.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        <section>
          <h2 className="text-lg font-semibold mb-3">{ta('recent_model_logs')}</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="p-2 text-left">{ta('col_type')}</th>
                <th className="p-2 text-left">{ta('col_model')}</th>
                <th className="p-2 text-left">{ta('col_status')}</th>
                <th className="p-2 text-left">{ta('col_latency')}</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_logs.map(log => (
                <tr key={log.id} className="border-t">
                  <td className="p-2">{log.request_type}</td>
                  <td className="p-2 font-mono text-xs">{log.model_used}</td>
                  <td className="p-2">{log.success ? <span className="text-green-600">✓</span> : <span className="text-red-600">✗</span>}</td>
                  <td className="p-2">{log.latency_ms ? `${(log.latency_ms / 1000).toFixed(1)}s` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  )
}
