'use client'

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
  secondary?: string
}

export function HeroSection({ title, subtitle, action, secondary }: HeroSectionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className="mb-8"
    >
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-[36px] font-bold leading-[1.1] text-v2-text-primary">
            {title}
          </h1>
          <p className="mt-2 text-base text-v2-text-secondary">
            {subtitle}
          </p>
          {secondary && (
            <p className="mt-1 text-sm font-medium text-v2-accent">
              {secondary}
            </p>
          )}
        </div>
        {action && (
          <Link
            href={action.href}
            className="flex items-center gap-2 px-5 h-10 rounded-xl bg-v2-accent text-white text-sm font-medium hover:bg-v2-accent-hover transition-colors duration-150 shrink-0"
          >
            {action.label}
            <ArrowRight className="w-4 h-4" />
          </Link>
        )}
      </div>
    </motion.div>
  )
}
