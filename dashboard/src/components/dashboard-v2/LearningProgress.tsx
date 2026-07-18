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
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
      className="rounded-[20px] border border-v2-border bg-v2-surface p-6"
    >
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full border border-v2-accent text-v2-accent">
          <Target className="h-5 w-5" />
        </div>
        <div>
          <p className="verge-label text-v2-accent">{safePercent.toFixed(0)}% complete</p>
          <h2 className="text-xl font-black leading-none text-v2-text-primary">{title}</h2>
        </div>
      </div>

      <div className="mb-5 h-3 overflow-hidden rounded-full border border-v2-border bg-v2-bg">
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
            <div key={i} className="flex items-center gap-3 rounded-[20px] border border-v2-border bg-v2-bg px-3 py-2">
              {m.completed ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-v2-accent" />
              ) : (
                <Circle className="h-4 w-4 shrink-0 text-v2-text-secondary" />
              )}
              <span
                className={`text-sm ${
                  m.completed ? 'text-v2-text-primary' : 'text-v2-text-secondary'
                }`}
              >
                {m.label}
              </span>
            </div>
          ))}
        </div>
      )}
    </motion.section>
  )
}
