'use client'

import type { ReactNode } from 'react'

interface PageHeaderProps {
  icon: ReactNode
  title: string
  description?: string
  actions?: ReactNode
}

export default function PageHeader({ icon, title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-8">
      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-primary/10 text-primary mt-0.5">
          {icon}
        </div>
        <div>
          <h1 className="text-display text-foreground">{title}</h1>
          {description && (
            <p className="text-small text-foreground-muted mt-1.5 max-w-xl">{description}</p>
          )}
        </div>
      </div>
      {actions && (
        <div className="flex items-center gap-3 shrink-0">
          {actions}
        </div>
      )}
    </div>
  )
}
