'use client'

import type { ReactNode } from 'react'

type CardVariant = 'default' | 'elevated' | 'accent'

interface CardProps {
  variant?: CardVariant
  className?: string
  children: ReactNode
  onClick?: () => void
}

const variantStyles: Record<CardVariant, string> = {
  default: 'bg-card rounded-xl border border-border',
  elevated: 'bg-card rounded-xl border border-border shadow-lg shadow-black/20',
  accent: 'bg-card rounded-xl border border-border border-t-2 border-t-primary',
}

export default function Card({ variant = 'default', className = '', children, onClick }: CardProps) {
  const Component = onClick ? 'button' : 'div'
  return (
    <Component
      className={`p-5 transition-colors ${variantStyles[variant]} ${onClick ? 'cursor-pointer hover:bg-card-hover text-left w-full' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </Component>
  )
}
