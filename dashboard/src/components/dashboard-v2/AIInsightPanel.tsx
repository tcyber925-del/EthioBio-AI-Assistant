'use client'

import { motion } from 'framer-motion'
import { Lightbulb, ArrowRight } from 'lucide-react'

interface AIInsightPanelProps {
  insights: string[]
}

export function AIInsightPanel({ insights }: AIInsightPanelProps) {
  if (insights.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
      className="bg-v2-surface rounded-[20px] border border-v2-border p-6 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)]"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 rounded-lg bg-v2-accent-muted text-v2-accent">
          <Lightbulb className="w-5 h-5" />
        </div>
        <h2 className="text-lg font-semibold text-v2-text-primary">AI Insights</h2>
      </div>
      <div className="space-y-3">
        {insights.map((insight, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-v2-bg">
            <ArrowRight className="w-4 h-4 text-v2-accent mt-0.5 shrink-0" />
            <p className="text-sm text-v2-text-primary leading-relaxed">{insight}</p>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
