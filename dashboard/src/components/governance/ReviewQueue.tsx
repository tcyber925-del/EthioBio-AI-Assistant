'use client'

import { useState } from 'react'
import { AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import ReviewDetail from './ReviewDetail'

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

interface ReviewQueueProps {
  items: ReviewItem[]
  onResolve: (traceId: string, notes: string) => void
  loading: boolean
}

export default function ReviewQueue({ items, onResolve, loading }: ReviewQueueProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (loading) {
    return <div className="text-gray-500">Loading review queue...</div>
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <CheckCircle className="mx-auto h-12 w-12 mb-3" />
        <p className="text-lg">No items pending review</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.trace_id} className="border rounded-lg">
          <button
            onClick={() => setExpandedId(expandedId === item.trace_id ? null : item.trace_id)}
            className="w-full flex items-center justify-between p-4 hover:bg-gray-50 text-left"
          >
            <div className="flex items-center gap-3 min-w-0">
              {item.reviewed ? (
                <CheckCircle className="h-5 w-5 text-green-500 shrink-0" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-500 shrink-0" />
              )}
              <div className="min-w-0">
                <p className="text-sm text-gray-900 truncate max-w-md">
                  {item.user_message}
                </p>
                <p className="text-xs text-gray-500">
                  {item.intent} &middot; Grade {item.grade_level ?? 'N/A'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {item.safety_issues.slice(0, 2).map((issue) => (
                <span key={issue} className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                  {issue}
                </span>
              ))}
              {item.reviewed ? (
                <span className="text-xs text-green-600 flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" /> Reviewed
                </span>
              ) : (
                <span className="text-xs text-yellow-600 flex items-center gap-1">
                  <Clock className="h-3 w-3" /> Pending
                </span>
              )}
            </div>
          </button>
          {expandedId === item.trace_id && (
            <ReviewDetail item={item} onResolve={onResolve} />
          )}
        </div>
      ))}
    </div>
  )
}
