'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import ReviewDetail from './ReviewDetail'
import Badge from '@/components/ui/Badge'

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
  const t = useTranslations('governance')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (loading) {
    return <div className="text-foreground-muted text-body">{t('loading')}</div>
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-foreground-muted">
        <CheckCircle className="mx-auto h-12 w-12 mb-3 text-foreground-muted/40" />
        <p className="text-body text-foreground-muted">{t('empty')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.trace_id} className="bg-card border border-border rounded-xl overflow-hidden">
          <button
            onClick={() => setExpandedId(expandedId === item.trace_id ? null : item.trace_id)}
            className="w-full flex items-center justify-between p-4 hover:bg-background-secondary text-left transition-colors"
          >
            <div className="flex items-center gap-3 min-w-0">
              {item.reviewed ? (
                <CheckCircle className="h-5 w-5 text-green-400 shrink-0" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-400 shrink-0" />
              )}
              <div className="min-w-0">
                <p className="text-body text-foreground truncate max-w-md">
                  {item.user_message}
                </p>
                <p className="text-small text-foreground-muted">
                  {item.intent} &middot; {t('grade_label', { grade: item.grade_level ?? 'N/A' })}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {item.safety_issues.slice(0, 2).map((issue) => (
                <Badge key={issue} variant="red">{issue}</Badge>
              ))}
              {item.reviewed ? (
                <span className="text-small text-green-400 flex items-center gap-1">
                  <CheckCircle className="h-3 w-3" /> {t('reviewed')}
                </span>
              ) : (
                <span className="text-small text-yellow-400 flex items-center gap-1">
                  <Clock className="h-3 w-3" /> {t('pending')}
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
