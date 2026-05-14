'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, BarChart3, AlertTriangle } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const mockData = [
  { topic: 'Cell Biology', score: 85 },
  { topic: 'Genetics', score: 45 },
  { topic: 'Evolution', score: 72 },
  { topic: 'Ecology', score: 90 },
  { topic: 'Biochemistry', score: 38 },
]

export default function StudentDetailPage() {
  const params = useParams()
  const grade = params.id === '1' ? 9 : params.id === '2' ? 10 : params.id === '3' ? 11 : 12

  return (
    <div>
      <Link href="/students" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to students
      </Link>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Grade {grade} Students</h1>
          <p className="text-sm text-gray-500 mt-1">Performance overview</p>
        </div>
      </div>

      {mockData.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No progress data yet</p>
          <p className="text-sm text-gray-400 mt-1">Data will appear after students take quizzes</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-sm border p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Topic Scores</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={mockData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="topic" width={100} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="score" fill="#16a34a" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-4">
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Weak Areas</h2>
              {mockData.filter(d => d.score < 60).length > 0 ? (
                <div className="space-y-2">
                  {mockData.filter(d => d.score < 60).map(d => (
                    <div key={d.topic} className="flex items-center gap-2 p-3 bg-red-50 rounded-lg">
                      <AlertTriangle className="w-4 h-4 text-red-500" />
                      <span className="text-sm text-red-700">{d.topic} ({d.score}%)</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">No weak areas identified</p>
              )}
            </div>
            <div className="bg-white rounded-xl shadow-sm border p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Summary</h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500">Average Score</p>
                  <p className="text-xl font-bold text-gray-900">
                    {Math.round(mockData.reduce((a, b) => a + b.score, 0) / mockData.length)}%
                  </p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500">Topics</p>
                  <p className="text-xl font-bold text-gray-900">{mockData.length}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
