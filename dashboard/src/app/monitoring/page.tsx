'use client'

import { useEffect, useState } from 'react'
import { BarChart3, AlertTriangle } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { PieChart, Pie, Cell, ResponsiveContainer, Legend } from 'recharts'

interface MonitoringData {
  total_requests: number; failed_requests: number
  fallback_rate: number; fallbacks: number
}

export default function MonitoringPage() {
  const [data, setData] = useState<MonitoringData | null>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = () => {
    setLoading(true)
    Promise.all([
      fetch('/api/admin/monitoring').then(r => r.json()),
      fetch('/api/admin/dashboard').then(r => r.json()),
    ])
      .then(([mon, dash]) => {
        setData(mon)
        setLogs(dash.recent_logs || [])
        setError(null)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [])

  if (loading) return <div className="grid grid-cols-1 md:grid-cols-3 gap-5">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  if (error) return (
    <div className="text-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-red-500">{error}</p>
    </div>
  )

  const pieData = [
    { name: 'Success', value: logs.filter(l => l.success).length },
    { name: 'Failed', value: logs.filter(l => !l.success).length },
  ]
  const COLORS = ['#16a34a', '#dc2626']

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Monitoring</h1>
          <p className="text-sm text-gray-500 mt-1">System performance and request tracking</p>
        </div>
        <button onClick={fetchData} className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50">Refresh</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-8">
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <p className="text-sm text-gray-500">Total Requests</p>
          <p className="text-2xl font-bold text-gray-900">{data?.total_requests ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <p className="text-sm text-gray-500">Failed</p>
          <p className="text-2xl font-bold text-red-600">{data?.failed_requests ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <p className="text-sm text-gray-500">Fallback Rate</p>
          <p className="text-2xl font-bold text-orange-600">{data?.fallback_rate ?? 0}%</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <p className="text-sm text-gray-500">Fallbacks Used</p>
          <p className="text-2xl font-bold text-gray-900">{data?.fallbacks ?? 0}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Request Success Rate</h2>
          {logs.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} dataKey="value" label>
                  {pieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                </Pie>
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-sm py-12 text-center">No data yet</p>
          )}
        </div>
        <div className="bg-white rounded-xl shadow-sm border p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Model Usage</h2>
          {logs.length > 0 ? (
            <div className="space-y-2 max-h-[250px] overflow-y-auto">
              {Object.entries(
                logs.reduce((acc: Record<string, number>, l) => {
                  const m = l.model_used || 'unknown'
                  acc[m] = (acc[m] || 0) + 1
                  return acc
                }, {})
              ).map(([model, count]) => (
                <div key={model} className="flex items-center justify-between p-2 hover:bg-gray-50 rounded">
                  <span className="text-sm font-mono text-gray-700">{model}</span>
                  <span className="text-sm font-semibold text-gray-900">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm py-12 text-center">No data yet</p>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border">
        <div className="px-5 py-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Request Logs</h2>
        </div>
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Latency</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((log: any, i: number) => (
                <tr key={log.id || i} className="hover:bg-gray-50">
                  <td className="px-5 py-3 text-sm text-gray-900">{log.request_type}</td>
                  <td className="px-5 py-3 text-sm text-gray-500 font-mono text-xs">{log.model_used}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      log.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>{log.success ? 'Success' : 'Failed'}</span>
                  </td>
                  <td className="px-5 py-3 text-sm text-gray-500">{log.latency_ms}ms</td>
                  <td className="px-5 py-3 text-sm text-gray-400">{log.created_at?.slice(11, 19) || '-'}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-12 text-center text-gray-400">No logs yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
