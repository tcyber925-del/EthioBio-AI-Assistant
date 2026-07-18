'use client'

import Link from 'next/link'
import { ChevronRight } from 'lucide-react'

interface BreadcrumbItem {
  label: string
  href?: string
}

interface ContextHeaderProps {
  items: BreadcrumbItem[]
}

export function ContextHeader({ items }: ContextHeaderProps) {
  return (
    <nav aria-label="Breadcrumb" className="flex h-10 items-center gap-2 text-v2-text-secondary verge-label">
      {items.map((item, i) => (
        <div key={i} className="flex items-center gap-2 min-w-0">
          {i > 0 && <ChevronRight className="h-3.5 w-3.5 shrink-0 text-v2-purple-rule" />}
          {item.href ? (
            <Link
              href={item.href}
              className="truncate transition-colors duration-150 hover:text-v2-link-hover focus-visible:verge-focus"
            >
              {item.label}
            </Link>
          ) : (
            <span aria-current="page" className="truncate text-v2-accent">{item.label}</span>
          )}
        </div>
      ))}
    </nav>
  )
}
