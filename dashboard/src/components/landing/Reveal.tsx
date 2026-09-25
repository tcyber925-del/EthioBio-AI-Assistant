'use client'

import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { motion as motionTokens } from '@/styles/design-system'

const REVEAL_DURATION = Number.parseInt(motionTokens.reveal, 10) / 1000

/**
 * Scroll reveal: rises and fades in once, then stays. Framer-motion
 * (`whileInView`) rather than the source design's IntersectionObserver +
 * CSS-keyframe variant — this matches the dashboard's motion convention, and
 * `MotionConfig reducedMotion="user"` (marketing layout) disables it for
 * visitors who ask for reduced motion.
 *
 * `delay` is in ms so callers can stagger grids (`index * 100`).
 */
export function Reveal({
  children,
  className = '',
  delay = 0,
}: {
  children: ReactNode
  className?: string
  delay?: number
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24, scale: 0.98 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{
        duration: REVEAL_DURATION,
        delay: delay / 1000,
        ease: motionTokens.revealEasing,
      }}
    >
      {children}
    </motion.div>
  )
}

/**
 * Technical mono label (`.label-mono`). Defaults to `text-meta`; passing any
 * `text-*` class replaces the default instead of fighting it for cascade order.
 */
export function Label({ children, className = '' }: { children: ReactNode; className?: string }) {
  const hasTextColor = /(^|\s)text-/.test(className)
  return (
    <p className={`label-mono ${hasTextColor ? '' : 'text-meta'} ${className}`}>{children}</p>
  )
}
