'use client'

import { useTranslations } from 'next-intl'
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
  const t = useTranslations('gamification')
  const remaining = totalTasks - completedTasks

  if (totalTasks === 0 && activePlans === 0) {
    return (
      <div className="bg-card rounded-xl border border-border p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2.5 rounded-lg bg-accent-teal/10 text-accent-teal">
            <ClipboardList className="w-5 h-5" />
          </div>
          <div>
            <p className="text-small text-foreground-muted">{t('recovery_progress')}</p>
            <p className="text-heading text-foreground">{t('no_recovery_plans')}</p>
          </div>
        </div>
        <p className="text-small text-foreground-muted/60 mt-2">
          {t('recovery_desc')}
        </p>
      </div>
    )
  }

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-accent-teal/10 text-accent-teal">
          <ClipboardList className="w-5 h-5" />
        </div>
        <div>
          <p className="text-small text-foreground-muted">{t('recovery_progress')}</p>
          <p className="text-heading text-foreground">
            {t('tasks_progress', { completed: completedTasks, total: totalTasks })}
          </p>
        </div>
      </div>

      {activePlans > 0 && (
        <p className="text-small text-foreground-muted mb-2">
          {t(activePlans === 1 ? 'active_plans_count' : 'active_plans_count_plural', { count: activePlans })}
        </p>
      )}

      <div className="w-full bg-border rounded-full h-2.5 overflow-hidden">
        <div
          className="bg-accent-teal h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(overallProgressPct, 100)}%` }}
        />
      </div>

      <div className="mt-2 flex items-center justify-between text-small text-foreground-muted/60">
        <span>{t('percent_complete', { pct: overallProgressPct })}</span>
        {remaining > 0 && (
          <span>{t(remaining === 1 ? 'tasks_remaining' : 'tasks_remaining_plural', { count: remaining })}</span>
        )}
      </div>
    </div>
  )
}
