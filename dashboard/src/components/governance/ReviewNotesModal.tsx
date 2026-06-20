'use client'

import { useState } from 'react'

interface ReviewNotesModalProps {
  traceId: string
  onConfirm: (notes: string) => void
  onCancel: () => void
}

export default function ReviewNotesModal({ traceId, onConfirm, onCancel }: ReviewNotesModalProps) {
  const [notes, setNotes] = useState('')

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md mx-4">
        <h3 className="text-heading text-foreground mb-2">Resolve Review Item</h3>
        <p className="text-small text-foreground-muted mb-4">Trace: {traceId}</p>

        <label className="block text-body text-foreground-muted mb-1">
          Review Notes (optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add notes about your review..."
          className="w-full border border-border rounded-lg p-3 text-body bg-background text-foreground placeholder:text-foreground-muted/50 h-24 resize-none focus:outline-none focus:ring-2 focus:ring-primary"
        />

        <div className="flex justify-end gap-3 mt-4">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-body text-foreground-muted hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(notes)}
            className="px-4 py-2 bg-primary text-white text-body rounded-lg hover:bg-primary-hover transition-colors"
          >
            Confirm & Resolve
          </button>
        </div>
      </div>
    </div>
  )
}
