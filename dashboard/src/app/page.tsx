'use client'

import { useEffect, useState } from 'react'
import { BookOpen, ClipboardCheck, FileText, Users, BarChart3, AlertTriangle } from 'lucide-react'
import StatCard from '@/components/StatCard'
import { CardSkeleton, TableSkeleton } from '@/components/Skeleton'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface DashboardData {
  users: number; teachers: number; students: number
  quizzes: number; lesson_plans: number; quiz_attempts: number
  recent_logs: Array<{
    id: string; request_type: string; model_used: string
    success: boolean; latency_ms: number; created_at: string
  }>
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/dashboard')
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Server returned ${res.status}: ${text}`)
      }
      const d = await res.json()
      setData(d)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  if (loading && !data) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
          {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
        <TableSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <p className="text-red-500 font-medium">Failed to load dashboard</p>
          <p className="text-sm text-gray-400 mt-1">{error}</p>
          <button onClick={fetchData} className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
            Retry
          </button>
        </div>
      </div>
    )
  }

  const logs = data?.recent_logs || []
  const successCount = logs.filter(l => l.success).length
  const failCount = logs.filter(l => !l.success).length

  const chartData = logs.slice().reverse().map((l, i) => ({
    name: `#${i + 1}`,
    latency: l.latency_ms,
    success: l.success ? 1 : 0,
  }))

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">EthioBio AI Assistant overview</p>
        </div>
        <button onClick={fetchData} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50 transition-colors">
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
        <StatCard icon={<Users className="w-6 h-6" />} label="Total Users" value={data?.users ?? 0} color="blue" subtitle="platform users" />
        <StatCard icon={<Users className="w-6 h-6" />} label="Teachers" value={data?.teachers ?? 0} color="green" />
        <StatCard icon={<Users className="w-6 h-6" />} label="Students" value={data?.students ?? 0} color="purple" />
        <StatCard icon={<ClipboardCheck className="w-6 h-6" />} label="Quizzes" value={data?.quizzes ?? 0} color="orange" />
        <StatCard icon={<FileText className="w-6 h-6" />} label="Lesson Plans" value={data?.lesson_plans ?? 0} color="indigo" />
        <StatCard icon={<BarChart3 className="w-6 h-6" />} label="Quiz Attempts" value={data?.quiz_attempts ?? 0} color="teal" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Request Latency</h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} unit="ms" />
                <Tooltip />
                <Line type="monotone" dataKey="latency" stroke="#16a34a" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-sm py-8 text-center">No request data yet</p>
          )}
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Request Status</h2>
          {logs.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                <span className="text-sm font-medium text-green-700">Success</span>
                <span className="text-lg font-bold text-green-700">{successCount}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                <span className="text-sm font-medium text-red-700">Failed</span>
                <span className="text-lg font-bold text-red-700">{failCount}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm font-medium text-gray-600">Success rate</span>
                <span className="text-lg font-bold text-gray-700">
                  {logs.length > 0 ? Math.round(successCount / logs.length * 100) : 0}%
                </span>
              </div>
            </div>
          ) : (
            <p className="text-gray-400 text-sm py-8 text-center">No data yet</p>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border">
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Recent Activity</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.slice(0, 10).map(log => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3 text-sm text-gray-900">{log.request_type}</td>
                  <td className="px-5 py-3 text-sm text-gray-500 font-mono text-xs">{log.model_used}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      log.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {log.success ? 'Success' : 'Failed'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-sm text-gray-500">{log.latency_ms}ms</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={4} className="px-5 py-12 text-center text-gray-400">No recent activity</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
