'use client'

import { motion } from 'framer-motion'
import { Target, CheckCircle2, Circle } from 'lucide-react'

interface Milestone {
  label: string
  completed: boolean
}

interface LearningProgressProps {
  title: string
  percent: number
  milestones: Milestone[]
}

export function LearningProgress({ title, percent, milestones }: LearningProgressProps) {
  const safePercent = Math.min(100, Math.max(0, percent))
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
      className="bg-v2-surface rounded-[20px] border border-v2-border p-6 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)]"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 rounded-lg bg-v2-accent-muted text-v2-accent">
          <Target className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-v2-text-primary">{title}</h2>
          <p className="text-xs text-v2-text-secondary">{safePercent}% complete</p>
        </div>
      </div>

      <div className="h-2 bg-v2-border rounded-full overflow-hidden mb-5">
        <motion.div
          initial={{ width: 0 }}
            animate={{ width: `${safePercent}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="h-full rounded-full bg-v2-accent"
        />
      </div>

      {milestones.length > 0 && (
        <div className="space-y-2">
          {milestones.map((m, i) => (
            <div key={i} className="flex items-center gap-3">
              {m.completed ? (
                <CheckCircle2 className="w-4 h-4 text-v2-accent shrink-0" />
              ) : (
                <Circle className="w-4 h-4 text-v2-text-secondary/40 shrink-0" />
              )}
              <span
                className={`text-sm ${
                  m.completed ? 'text-v2-text-primary' : 'text-v2-text-secondary/60'
                }`}
              >
                {m.label}
              </span>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  )
}
