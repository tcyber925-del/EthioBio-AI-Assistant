'use client'

import { useEffect, useState, useCallback } from 'react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import ReviewQueue from '@/components/governance/ReviewQueue'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { ErrorAlert } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

interface ReviewItem {
  trace_id: string
  user_message: string
  response: string | null
  intent: string
  grade_level: number | null
  language: string | null
  safety_issues: string[]
  safety_action: string
  groundedness_score: number
  hallucination_rate: number
  requires_teacher_review: boolean
  reviewed: boolean
  review_notes: string | null
  reviewed_at: string | null
  created_at: string | null
}

interface ReviewListResponse {
  traces: ReviewItem[]
  total: number
  limit: number
  offset: number
}

type FilterTab = 'pending' | 'resolved'

export default function AdminReviewPage() {
  const t = useTranslations('admin.review')
  const [items, setItems] = useState<ReviewItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)
  const [resolveError, setResolveError] = useState<AppError | null>(null)
  const [filter, setFilter] = useState<FilterTab>('pending')

  const fetchItems = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchWithAuth(
        `/api/admin/review?status=${filter}&limit=50`
      )
      const data: ReviewListResponse = await response.json()
      setItems(data.traces)
      setTotal(data.total)
    } catch (err) {
      setError(normalizeException(err))
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  const handleResolve = async (traceId: string, notes: string) => {
    setResolveError(null)
    try {
      await fetchWithAuth(`/api/admin/review/${traceId}`, {
        method: 'PATCH',
        body: JSON.stringify({ action: 'resolve', review_notes: notes }),
        headers: { 'Content-Type': 'application/json' },
      })
      fetchItems()
    } catch (err) {
      setResolveError(normalizeException(err))
    }
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-heading text-foreground">{t('title')}</h1>
          <p className="text-small text-foreground-muted mt-1">
            {t('subtitle')}
          </p>
        </div>
      </div>

      <Card className="mb-6">
        <div className="flex gap-2">
          <Button
            variant={filter === 'pending' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setFilter('pending')}
          >
            {t('filter_pending')} ({filter === 'pending' ? total : '...'})
          </Button>
          <Button
            variant={filter === 'resolved' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setFilter('resolved')}
          >
            {t('filter_resolved')}
          </Button>
        </div>
      </Card>

      {error && (
        <ErrorAlert
          error={error}
          title={t('error_load')}
          onRetry={() => void fetchItems()}
          retrying={loading}
          className="mb-4"
        />
      )}

      {resolveError && (
        <ErrorAlert error={resolveError} title={t('error_resolve')} className="mb-4" />
      )}

      <ReviewQueue items={items} onResolve={handleResolve} loading={loading} />
    </div>
  )
}
