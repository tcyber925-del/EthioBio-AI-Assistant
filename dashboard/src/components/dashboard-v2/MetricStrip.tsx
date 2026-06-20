'use client'

import { motion } from 'framer-motion'

interface Metric {
  label: string
  value: string | number
  accent?: boolean
}

interface MetricStripProps {
  metrics: Metric[]
}

export function MetricStrip({ metrics }: MetricStripProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className="bg-v2-surface rounded-[20px] border border-v2-border shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)]"
    >
      <div className="flex divide-x divide-v2-border">
        {metrics.map((m, i) => (
          <div
            key={i}
            className={`flex-1 px-6 py-4 ${m.accent ? 'bg-v2-accent-muted rounded-l-[20px]' : ''}`}
          >
            <p className="text-xs text-v2-text-secondary font-medium">{m.label}</p>
            <p className={`text-xl font-bold mt-0.5 ${m.accent ? 'text-v2-accent' : 'text-v2-text-primary'}`}>
              {m.value}
            </p>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
