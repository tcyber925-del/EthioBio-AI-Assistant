'use client'

import { useState } from 'react'
import ReviewNotesModal from './ReviewNotesModal'

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

interface ReviewDetailProps {
  item: ReviewItem
  onResolve: (traceId: string, notes: string) => void
}

export default function ReviewDetail({ item, onResolve }: ReviewDetailProps) {
  const [showModal, setShowModal] = useState(false)

  const scoreColor = (score: number) => {
    if (score >= 0.7) return 'text-green-600'
    if (score >= 0.4) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="border-t px-4 py-4 space-y-4 bg-gray-50">
      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">User Message</h4>
        <p className="text-sm text-gray-900">{item.user_message}</p>
      </div>

      <div>
        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Response</h4>
        <p className="text-sm text-gray-900 whitespace-pre-wrap">{item.response ?? '(no response)'}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Safety Issues</h4>
          {item.safety_issues.length > 0 ? (
            <ul className="text-sm text-red-600 list-disc list-inside">
              {item.safety_issues.map((issue) => <li key={issue}>{issue}</li>)}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">None</p>
          )}
        </div>
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Safety Action</h4>
          <p className="text-sm text-gray-900">{item.safety_action || 'N/A'}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Groundedness</h4>
          <p className={`text-sm font-medium ${scoreColor(item.groundedness_score)}`}>
            {(item.groundedness_score * 100).toFixed(0)}%
          </p>
        </div>
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Hallucination Rate</h4>
          <p className={`text-sm font-medium ${scoreColor(1 - item.hallucination_rate)}`}>
            {(item.hallucination_rate * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {item.review_notes && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Review Notes</h4>
          <p className="text-sm text-gray-700 italic">{item.review_notes}</p>
        </div>
      )}

      {!item.reviewed && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            Resolve
          </button>
        </div>
      )}

      {showModal && (
        <ReviewNotesModal
          traceId={item.trace_id}
          onConfirm={(notes) => { onResolve(item.trace_id, notes); setShowModal(false) }}
          onCancel={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
