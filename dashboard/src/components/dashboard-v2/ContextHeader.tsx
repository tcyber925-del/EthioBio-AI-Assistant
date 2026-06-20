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
    <nav className="flex items-center gap-1.5 h-10 text-sm text-v2-text-secondary">
      {items.map((item, i) => (
        <div key={i} className="flex items-center gap-1.5">
          {i > 0 && <ChevronRight className="w-3.5 h-3.5 text-v2-text-secondary/40" />}
          {item.href ? (
            <Link
              href={item.href}
              className="hover:text-v2-text-primary transition-colors duration-150"
            >
              {item.label}
            </Link>
          ) : (
            <span className="text-v2-text-primary font-medium">{item.label}</span>
          )}
        </div>
      ))}
    </nav>
  )
}
