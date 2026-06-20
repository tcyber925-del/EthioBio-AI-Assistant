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
      whileHover={{ y: -2, boxShadow: '0 2px 4px rgba(0,0,0,.04), 0 20px 48px rgba(0,0,0,.08)' }}
      className="bg-v2-surface rounded-[20px] border border-v2-border p-6 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)] transition-shadow duration-150"
    >
      <p className="text-sm text-v2-text-secondary font-medium">{title}</p>
      <p className="mt-2 text-[36px] font-bold leading-[1.1] text-v2-text-primary">
        {value}
      </p>
      {trend && (
        <div className="mt-2 flex items-center gap-1.5">
          {trend.direction === 'up' && (
            <TrendingUp className="w-4 h-4 text-v2-success" />
          )}
          {trend.direction === 'down' && (
            <TrendingDown className="w-4 h-4 text-v2-error" />
          )}
          <span
            className={`text-sm font-medium ${
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
        <p className="mt-1 text-xs text-v2-text-secondary/60">{context}</p>
      )}
    </motion.div>
  )
}
