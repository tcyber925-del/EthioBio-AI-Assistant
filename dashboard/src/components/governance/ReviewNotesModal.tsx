'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'

interface ReviewNotesModalProps {
  traceId: string
  onConfirm: (notes: string) => void
  onCancel: () => void
}

export default function ReviewNotesModal({ traceId, onConfirm, onCancel }: ReviewNotesModalProps) {
  const t = useTranslations('governance')
  const tc = useTranslations('common')
  const [notes, setNotes] = useState('')

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md mx-4">
        <h3 className="text-heading text-foreground mb-2">{t('modal_title')}</h3>
        <p className="text-small text-foreground-muted mb-4">{t('trace_label', { id: traceId })}</p>

        <label className="block text-body text-foreground-muted mb-1">
          {t('notes_label')}
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder={t('notes_placeholder')}
          className="w-full border border-border rounded-lg p-3 text-body bg-background text-foreground placeholder:text-foreground-muted/50 h-24 resize-none focus:outline-none focus:ring-2 focus:ring-primary"
        />

        <div className="flex justify-end gap-3 mt-4">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-body text-foreground-muted hover:text-foreground transition-colors"
          >
            {tc('cancel')}
          </button>
          <button
            onClick={() => onConfirm(notes)}
            className="px-4 py-2 bg-primary text-white text-body rounded-lg hover:bg-primary-hover transition-colors"
          >
            {t('confirm_resolve')}
          </button>
        </div>
      </div>
    </div>
  )
}
