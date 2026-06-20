'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'

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

  if (error) return <p className="text-red-400">{tcommon('error')}: {error}</p>
  if (loading) return <p className="text-foreground-muted text-body">{tcommon('loading')}</p>

  const statusBadge = (s: string) => {
    switch (s) {
      case 'published': return <Badge variant="green">{s}</Badge>
      case 'draft': return <Badge variant="yellow">{s}</Badge>
      default: return <Badge variant="muted">{s}</Badge>
    }
  }

  return (
    <div>
      <h1 className="text-heading text-foreground mb-6">{tc('title')}</h1>
      <Card className="mb-6">
        <div className="flex gap-4">
          <select value={type} onChange={e => setType(e.target.value)} className="px-4 py-2 border border-border rounded-lg text-body bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="all">{tc('all_types')}</option>
            <option value="quiz">{tc('quiz')}</option>
            <option value="lesson">{tc('lesson')}</option>
          </select>
          <select value={status} onChange={e => setStatus(e.target.value)} className="px-4 py-2 border border-border rounded-lg text-body bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="all">{tc('all_status')}</option>
            <option value="draft">{tc('draft')}</option>
            <option value="published">{tc('published')}</option>
            <option value="archived">Archived</option>
          </select>
        </div>
      </Card>
      <Card className="p-0 overflow-hidden">
        <table className="w-full text-body">
          <thead>
            <tr className="bg-background-secondary">
              <th className="px-4 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{tc('col_title')}</th>
              <th className="px-4 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{tcommon('type')}</th>
              <th className="px-4 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{tcommon('grade')}</th>
              <th className="px-4 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{tc('status_label')}</th>
              <th className="px-4 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{tcommon('created')}</th>
              <th className="px-4 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{tcommon('actions')}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item: ContentItem) => (
              <tr key={item.id} className="border-t border-border hover:bg-background-secondary/30 transition-colors">
                <td className="px-4 py-3 text-foreground">{item.title || item.topic}</td>
                <td className="px-4 py-3">
                  <Badge variant={item.question_count !== undefined ? 'blue' : 'purple'}>
                    {item.question_count !== undefined ? 'quiz' : 'lesson'}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-foreground-muted">{item.grade_level}</td>
                <td className="px-4 py-3">{statusBadge(item.status)}</td>
                <td className="px-4 py-3 text-foreground-muted">{item.created_at ? new Date(item.created_at).toLocaleDateString(locale) : '-'}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        const ct = item.question_count !== undefined ? 'quiz' : 'lesson'
                        router.push(`/admin/content/${ct}/${item.id}`)
                      }}
                      className="text-primary hover:text-primary-hover text-small transition-colors"
                    >{tcommon('view')}</button>
                    {item.status !== 'published' && (
                      <button onClick={() => updateStatus(item.question_count !== undefined ? 'quiz' : 'lesson', item.id, 'published')} className="text-green-400 hover:text-green-300 text-small transition-colors">{tc('publish')}</button>
                    )}
                    {item.status === 'published' && (
                      <button onClick={() => updateStatus(item.question_count !== undefined ? 'quiz' : 'lesson', item.id, 'archived')} className="text-red-400 hover:text-red-300 text-small transition-colors">{tc('archive')}</button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
