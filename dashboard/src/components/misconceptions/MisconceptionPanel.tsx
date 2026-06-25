import { AlertTriangle } from 'lucide-react'

export function MisconceptionPanel({ userId: _userId }: { userId: string }) {
  return (
    <div className="flex items-center justify-center py-8 border border-dashed border-border rounded-lg">
      <div className="flex flex-col items-center gap-2 text-foreground-muted">
        <AlertTriangle className="w-5 h-5" />
        <p className="text-caption">Misconception detection panel — coming soon</p>
      </div>
    </div>
  )
}
