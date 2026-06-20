'use client'

import type { ReactNode } from 'react'

type BadgeVariant = 'green' | 'yellow' | 'red' | 'muted' | 'blue' | 'purple' | 'orange'

interface BadgeProps {
  variant?: BadgeVariant
  className?: string
  children: ReactNode
}

const styles: Record<BadgeVariant, string> = {
  green: 'bg-green-500/10 text-green-400',
  yellow: 'bg-yellow-500/10 text-yellow-400',
  red: 'bg-red-500/10 text-red-400',
  blue: 'bg-blue-500/10 text-blue-400',
  purple: 'bg-purple-500/10 text-purple-400',
  orange: 'bg-orange-500/10 text-orange-400',
  muted: 'bg-border/50 text-foreground-muted',
}

export default function Badge({ variant = 'muted', className = '', children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[variant]} ${className}`}>
      {children}
    </span>
  )
}
