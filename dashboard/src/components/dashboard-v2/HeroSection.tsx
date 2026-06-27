'use client'

import { type ReactNode } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

interface HeroSectionProps {
  title: string
  subtitle: string
  action?: {
    label: string
    href: string
  }
  secondary?: ReactNode
}

export function HeroSection({ title, subtitle, action, secondary }: HeroSectionProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
      className="mb-8 border-b border-v2-border pb-6"
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          {secondary && (
            <div className="verge-label mb-3 text-v2-accent">{secondary}</div>
          )}
          <h1 className="verge-display max-w-5xl text-5xl text-v2-text-primary md:text-[60px] lg:text-[72px]">
            {title}
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-relaxed text-v2-text-secondary">
            {subtitle}
          </p>
        </div>
        {action && (
          <Link
            href={action.href}
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-[24px] bg-v2-accent px-6 text-sm font-bold text-v2-inverted transition-colors duration-150 hover:bg-white hover:text-v2-inverted focus-visible:verge-focus"
          >
            <span className="verge-label text-v2-inverted">{action.label}</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>
    </motion.section>
  )
}
