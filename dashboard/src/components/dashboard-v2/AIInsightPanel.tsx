'use client'

import { motion } from 'framer-motion'
import { Lightbulb, ArrowRight } from 'lucide-react'

interface AIInsightPanelProps {
  insights: string[]
}

export function AIInsightPanel({ insights }: AIInsightPanelProps) {
  if (insights.length === 0) return null

  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
      className="rounded-[20px] border border-v2-border bg-v2-surface p-6"
    >
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full border border-v2-accent text-v2-accent">
          <Lightbulb className="h-5 w-5" />
        </div>
        <div>
          <p className="verge-label text-v2-accent">AI Panel</p>
          <h2 className="text-xl font-black leading-none text-v2-text-primary">Insights</h2>
        </div>
      </div>
      <div className="space-y-3">
        {insights.map((insight, i) => (
          <div key={i} className="rounded-[20px] border border-v2-border bg-v2-bg p-4">
            <div className="flex items-start gap-3">
              <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-v2-accent" />
              <p className="text-sm leading-relaxed text-v2-text-primary">{insight}</p>
            </div>
          </div>
        ))}
      </div>
    </motion.section>
  )
}
