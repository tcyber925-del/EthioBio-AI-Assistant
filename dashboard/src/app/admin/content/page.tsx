'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export default function AdminContentPage() {
  const [items, setItems] = useState<any[]>([])
  const [type, setType] = useState('all')
  const [status, setStatus] = useState('all')
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    const fetchType = async (ct: string) => {
      const params = new URLSearchParams()
      params.set('content_type', ct)
      if (status !== 'all') params.set('status', status)
      const data = await fetchWithAuth(`/admin/content/review?${params}`)
      return data.items || []
    }
    if (type === 'all') {
      Promise.all([fetchType('quiz'), fetchType('lesson')])
        .then(([quizzes, lessons]) => setItems([...quizzes, ...lessons]))
        .catch(err => setError(err instanceof Error ? err.message : String(err)))
    } else {
      fetchType(type)
        .then(setItems)
        .catch(err => setError(err instanceof Error ? err.message : String(err)))
    }
  }, [type, status])

  const updateStatus = async (contentType: string, id: string, newStatus: string) => {
    await fetchWithAuth(`/admin/content/${contentType}/${id}/status?status=${newStatus}`, { method: 'PATCH' })
    setItems(prev => prev.map(i => i.id === id ? { ...i, status: newStatus } : i))
  }

  if (error) return <p className="text-red-600">Error: {error}</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Content Review</h1>
      <div className="flex gap-4 mb-4">
        <select value={type} onChange={e => setType(e.target.value)} className="border rounded px-3 py-2">
          <option value="all">All Types</option>
          <option value="quiz">Quizzes</option>
          <option value="lesson">Lessons</option>
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)} className="border rounded px-3 py-2">
          <option value="all">All Status</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-2 text-left">Title</th>
            <th className="p-2 text-left">Type</th>
            <th className="p-2 text-left">Grade</th>
            <th className="p-2 text-left">Status</th>
            <th className="p-2 text-left">Created</th>
            <th className="p-2 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item: any) => (
            <tr key={item.id} className="border-t">
              <td className="p-2">{item.title || item.topic}</td>
              <td className="p-2">
                <span className={`px-2 py-0.5 rounded text-xs ${item.question_count !== undefined ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>
                  {item.question_count !== undefined ? 'quiz' : 'lesson'}
                </span>
              </td>
              <td className="p-2">{item.grade_level}</td>
              <td className="p-2">
                <span className={`px-2 py-0.5 rounded text-xs ${
                  item.status === 'published' ? 'bg-green-100 text-green-700' :
                  item.status === 'draft' ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-700'
                }`}>{item.status}</span>
              </td>
              <td className="p-2 text-gray-500">{item.created_at ? new Date(item.created_at).toLocaleDateString() : '-'}</td>
              <td className="p-2 flex gap-2">
                <button
                  onClick={() => {
                    const ct = item.question_count !== undefined ? 'quiz' : 'lesson'
                    router.push(`/admin/content/${ct}/${item.id}`)
                  }}
                  className="text-blue-600 hover:underline text-xs"
                >View</button>
                {item.status !== 'published' && (
                  <button onClick={() => updateStatus(item.question_count !== undefined ? 'quiz' : 'lesson', item.id, 'published')} className="text-green-600 hover:underline text-xs">Publish</button>
                )}
                {item.status === 'published' && (
                  <button onClick={() => updateStatus(item.question_count !== undefined ? 'quiz' : 'lesson', item.id, 'archived')} className="text-red-600 hover:underline text-xs">Archive</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
