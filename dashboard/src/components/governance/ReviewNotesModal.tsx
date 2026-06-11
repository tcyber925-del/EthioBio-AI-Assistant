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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
        <h3 className="text-lg font-semibold mb-2">Resolve Review Item</h3>
        <p className="text-sm text-gray-500 mb-4">Trace: {traceId}</p>

        <label className="block text-sm font-medium text-gray-700 mb-1">
          Review Notes (optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Add notes about your review..."
          className="w-full border rounded-lg p-3 text-sm h-24 resize-none"
        />

        <div className="flex justify-end gap-3 mt-4">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(notes)}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
          >
            Confirm & Resolve
          </button>
        </div>
      </div>
    </div>
  )
}
