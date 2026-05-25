'use client'

import { ClipboardList } from 'lucide-react'

interface RecoveryProgressCardProps {
  activePlans: number
  totalTasks: number
  completedTasks: number
  overallProgressPct: number
}

export default function RecoveryProgressCard({
  activePlans,
  totalTasks,
  completedTasks,
  overallProgressPct,
}: RecoveryProgressCardProps) {
  if (totalTasks === 0 && activePlans === 0) {
    return (
      <div className="bg-card rounded-xl border border-border p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400">
            <ClipboardList className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm text-foreground-muted">Recovery Progress</p>
            <p className="text-lg font-bold text-foreground">No Recovery Plans</p>
          </div>
        </div>
        <p className="text-xs text-foreground-muted/60 mt-2">
          Complete quizzes to identify weak areas and start a recovery plan.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400">
          <ClipboardList className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-foreground-muted">Recovery Progress</p>
          <p className="text-lg font-bold text-foreground">
            {completedTasks}/{totalTasks} tasks
          </p>
        </div>
      </div>

      {activePlans > 0 && (
        <p className="text-xs text-foreground-muted mb-2">{activePlans} active plan{activePlans > 1 ? 's' : ''}</p>
      )}

      <div className="w-full bg-border rounded-full h-2.5">
        <div
          className="bg-emerald-400 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(overallProgressPct, 100)}%` }}
        />
      </div>

      <div className="mt-2 flex items-center justify-between text-xs text-foreground-muted/60">
        <span>{overallProgressPct}% complete</span>
        {totalTasks - completedTasks > 0 && (
          <span>{totalTasks - completedTasks} task{totalTasks - completedTasks > 1 ? 's' : ''} remaining</span>
        )}
      </div>
    </div>
  )
}
