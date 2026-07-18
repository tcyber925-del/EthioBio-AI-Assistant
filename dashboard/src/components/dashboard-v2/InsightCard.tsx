'use client'

import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface InsightCardProps {
  title: string
  value: string | number
  trend?: {
    direction: 'up' | 'down' | 'neutral'
    label: string
  }
  context?: string
  index?: number
}

export function InsightCard({ title, value, trend, context, index = 0 }: InsightCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.15,
        delay: index * 0.05,
        ease: [0.16, 1, 0.3, 1],
      }}
      className="rounded-[20px] border border-v2-border bg-v2-surface p-6 transition-colors duration-150 hover:border-v2-accent"
    >
      <p className="verge-label text-v2-text-secondary">{title}</p>
      <p className="mt-3 text-4xl font-black leading-none text-v2-text-primary">
        {value}
      </p>
      {trend && (
        <div className="mt-3 flex items-center gap-1.5">
          {trend.direction === 'up' && (
            <TrendingUp className="h-4 w-4 text-v2-success" />
          )}
          {trend.direction === 'down' && (
            <TrendingDown className="h-4 w-4 text-v2-error" />
          )}
          <span
            className={`verge-label ${
              trend.direction === 'up'
                ? 'text-v2-success'
                : trend.direction === 'down'
                ? 'text-v2-error'
                : 'text-v2-text-secondary'
            }`}
          >
            {trend.label}
          </span>
        </div>
      )}
      {context && (
        <p className="mt-2 text-xs leading-relaxed text-v2-text-secondary">{context}</p>
      )}
    </motion.div>
  )
}
