'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export const dynamic = 'force-dynamic'

interface ContentItem {
  id: string
  title?: string
  topic?: string
  grade_level?: number
  status: string
  created_at?: string
  question_count?: number
}

export default function AdminContentPage() {
  const locale = useLocale()
  const tc = useTranslations('admin.content')
  const tcommon = useTranslations('common')
  const [items, setItems] = useState<ContentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [type, setType] = useState('all')
  const [status, setStatus] = useState('all')
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    const fetchType = async (ct: string) => {
      const params = new URLSearchParams()
      params.set('content_type', ct)
      if (status !== 'all') params.set('status', status)
      const data = await fetchWithAuth(`/api/admin/content/review?${params}`)
      return data.items || []
    }
    if (type === 'all') {
      Promise.all([fetchType('quiz'), fetchType('lesson')])
        .then(([quizzes, lessons]) => {
          setItems([...quizzes, ...lessons])
          setLoading(false)
        })
        .catch(err => {
          setError(err instanceof Error ? err.message : String(err))
          setLoading(false)
        })
    } else {
      fetchType(type)
        .then(items => {
          setItems(items)
          setLoading(false)
        })
        .catch(err => {
          setError(err instanceof Error ? err.message : String(err))
          setLoading(false)
        })
    }
  }, [type, status])

  const updateStatus = async (contentType: string, id: string, newStatus: string) => {
    await fetchWithAuth(`/api/admin/content/${contentType}/${id}/status?status=${newStatus}`, { method: 'PATCH' })
    setItems(prev => prev.map(i => i.id === id ? { ...i, status: newStatus } : i))
  }

  if (error) return <p className="text-red-600">{tcommon('error')}: {error}</p>
  if (loading) return <p className="text-gray-500">{tcommon('loading')}</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{tc('title')}</h1>
      <div className="flex gap-4 mb-4">
        <select value={type} onChange={e => setType(e.target.value)} className="border rounded px-3 py-2">
          <option value="all">{tc('all_types')}</option>
          <option value="quiz">{tc('quiz')}</option>
          <option value="lesson">{tc('lesson')}</option>
        </select>
        <select value={status} onChange={e => setStatus(e.target.value)} className="border rounded px-3 py-2">
          <option value="all">{tc('all_status')}</option>
          <option value="draft">{tc('draft')}</option>
          <option value="published">{tc('published')}</option>
          <option value="archived">Archived</option>
        </select>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-2 text-left">{tc('col_title')}</th>
            <th className="p-2 text-left">{tcommon('type')}</th>
            <th className="p-2 text-left">{tcommon('grade')}</th>
            <th className="p-2 text-left">{tc('status_label')}</th>
            <th className="p-2 text-left">{tcommon('created')}</th>
            <th className="p-2 text-left">{tcommon('actions')}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item: ContentItem) => (
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
              <td className="p-2 text-gray-500">{item.created_at ? new Date(item.created_at).toLocaleDateString(locale) : '-'}</td>
              <td className="p-2 flex gap-2">
                <button
                  onClick={() => {
                    const ct = item.question_count !== undefined ? 'quiz' : 'lesson'
                    router.push(`/admin/content/${ct}/${item.id}`)
                  }}
                  className="text-blue-600 hover:underline text-xs"
                >{tcommon('view')}</button>
                {item.status !== 'published' && (
                  <button onClick={() => updateStatus(item.question_count !== undefined ? 'quiz' : 'lesson', item.id, 'published')} className="text-green-600 hover:underline text-xs">{tc('publish')}</button>
                )}
                {item.status === 'published' && (
                  <button onClick={() => updateStatus(item.question_count !== undefined ? 'quiz' : 'lesson', item.id, 'archived')} className="text-red-600 hover:underline text-xs">{tc('archive')}</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
