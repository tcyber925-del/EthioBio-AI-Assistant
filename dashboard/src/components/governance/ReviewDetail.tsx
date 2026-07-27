'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import ReviewNotesModal from './ReviewNotesModal'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'

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
  const t = useTranslations('governance')
  const [showModal, setShowModal] = useState(false)

  const scoreColor = (score: number) => {
    if (score >= 0.7) return 'text-green-400'
    if (score >= 0.4) return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <div className="border-t border-border px-5 py-4 space-y-4 bg-background-secondary/30">
      <div>
        <h4 className="text-small font-semibold text-foreground-muted uppercase tracking-wider mb-1">{t('user_message')}</h4>
        <p className="text-body text-foreground">{item.user_message}</p>
      </div>

      <div>
        <h4 className="text-small font-semibold text-foreground-muted uppercase tracking-wider mb-1">{t('response')}</h4>
        <p className="text-body text-foreground whitespace-pre-wrap">{item.response ?? t('no_response')}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-small font-semibold text-foreground-muted uppercase tracking-wider mb-1">{t('safety_issues')}</h4>
          {item.safety_issues.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {item.safety_issues.map((issue) => (
                <Badge key={issue} variant="red">{issue}</Badge>
              ))}
            </div>
          ) : (
            <p className="text-body text-foreground-muted">{t('none')}</p>
          )}
        </div>
        <div>
          <h4 className="text-small font-semibold text-foreground-muted uppercase tracking-wider mb-1">{t('safety_action')}</h4>
          <p className="text-body text-foreground">{item.safety_action || 'N/A'}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-small font-semibold text-foreground-muted uppercase tracking-wider mb-1">{t('groundedness')}</h4>
          <p className={`text-body font-medium ${scoreColor(item.groundedness_score)}`}>
            {(item.groundedness_score * 100).toFixed(0)}%
          </p>
        </div>
        <div>
          <h4 className="text-small font-semibold text-foreground-muted uppercase tracking-wider mb-1">{t('hallucination_rate')}</h4>
          <p className={`text-body font-medium ${scoreColor(1 - item.hallucination_rate)}`}>
            {(item.hallucination_rate * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {item.review_notes && (
        <div>
          <h4 className="text-small font-semibold text-foreground-muted uppercase tracking-wider mb-1">{t('review_notes')}</h4>
          <p className="text-body text-foreground-muted italic">{item.review_notes}</p>
        </div>
      )}

      {!item.reviewed && (
        <div className="flex justify-end pt-2">
          <Button variant="primary" size="sm" onClick={() => setShowModal(true)}>
            {t('resolve')}
          </Button>
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
