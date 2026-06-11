'use client'

import { useEffect, useState, useCallback } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import ReviewQueue from '@/components/governance/ReviewQueue'

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
  const [items, setItems] = useState<ReviewItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<FilterTab>('pending')

  const fetchItems = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data: ReviewListResponse = await fetchWithAuth(
        `/api/admin/review?status=${filter}&limit=50`
      )
      setItems(data.traces)
      setTotal(data.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load review items')
    } finally {
      setLoading(false)
    }
  }, [filter])

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  const handleResolve = async (traceId: string, notes: string) => {
    try {
      await fetchWithAuth(`/api/admin/review/${traceId}`, {
        method: 'PATCH',
        body: JSON.stringify({ action: 'resolve', review_notes: notes }),
        headers: { 'Content-Type': 'application/json' },
      })
      fetchItems()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resolve item')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Review Queue</h1>
          <p className="text-sm text-gray-500 mt-1">
            Pipeline responses flagged by the Safety Node for teacher review
          </p>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setFilter('pending')}
          className={`px-4 py-2 text-sm rounded-lg ${
            filter === 'pending'
              ? 'bg-yellow-100 text-yellow-800 font-medium'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Pending ({filter === 'pending' ? total : '...'})
        </button>
        <button
          onClick={() => setFilter('resolved')}
          className={`px-4 py-2 text-sm rounded-lg ${
            filter === 'resolved'
              ? 'bg-green-100 text-green-800 font-medium'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Resolved
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      <ReviewQueue items={items} onResolve={handleResolve} loading={loading} />
    </div>
  )
}
