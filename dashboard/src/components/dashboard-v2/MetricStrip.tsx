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
      transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
      className="overflow-hidden rounded-[20px] border border-v2-border"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px bg-v2-border">
        {metrics.map((m, i) => (
          <div
            key={i}
            className={`min-h-28 px-6 py-5 ${
              m.accent ? 'bg-v2-accent text-v2-inverted' : i % 2 === 0 ? 'bg-v2-surface' : 'bg-v2-bg'
            }`}
          >
            <p className={`verge-label ${m.accent ? 'text-v2-inverted/75' : 'text-v2-text-secondary'}`}>{m.label}</p>
            <p className={`mt-3 text-3xl font-black leading-none ${m.accent ? 'text-v2-inverted' : 'text-v2-text-primary'}`}>
              {m.value}
            </p>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
