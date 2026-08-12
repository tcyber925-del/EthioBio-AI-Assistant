'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import { ErrorBanner, ErrorState } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

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
  const [error, setError] = useState<AppError | null>(null)
  const [actionError, setActionError] = useState<AppError | null>(null)
  const router = useRouter()

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    const fetchType = async (ct: string) => {
      const params = new URLSearchParams()
      params.set('content_type', ct)
      if (status !== 'all') params.set('status', status)
      const response = await fetchWithAuth(`/api/admin/content/review?${params}`)
      const data = await response.json()
      return data.items || []
    }
    try {
      if (type === 'all') {
        const [quizzes, lessons] = await Promise.all([fetchType('quiz'), fetchType('lesson')])
        setItems([...quizzes, ...lessons])
      } else {
        setItems(await fetchType(type))
      }
    } catch (err) {
      setError(normalizeException(err))
    } finally {
      setLoading(false)
    }
  }, [type, status])

  useEffect(() => { load() }, [load])

  const updateStatus = async (contentType: string, id: string, newStatus: string) => {
    setActionError(null)
    try {
      await fetchWithAuth(`/api/admin/content/${contentType}/${id}/status?status=${newStatus}`, { method: 'PATCH' })
      setItems(prev => prev.map(i => i.id === id ? { ...i, status: newStatus } : i))
    } catch (err) {
      setActionError(normalizeException(err))
    }
  }

  if (error) return <ErrorState error={error} onRetry={() => void load()} />
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
            <option value="archived">{tc('archived')}</option>
          </select>
        </div>
      </Card>
      {actionError && (
        <div className="mb-6">
          <ErrorBanner error={actionError} />
        </div>
      )}
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
