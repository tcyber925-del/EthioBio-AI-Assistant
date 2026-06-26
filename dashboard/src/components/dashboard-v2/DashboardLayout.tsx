'use client'

import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { ContextHeader } from './ContextHeader'

interface DashboardLayoutProps {
  children: ReactNode
  breadcrumbs: { label: string; href?: string }[]
}

export function DashboardLayout({ children, breadcrumbs }: DashboardLayoutProps) {
  return (
    <>
      <header className="relative z-10 shrink-0 px-5 pt-4 pb-0 sm:px-8 lg:px-10">
        <ContextHeader items={breadcrumbs} />
      </header>
      <motion.main
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 flex-1 overflow-y-auto px-5 py-5 sm:px-8 lg:px-10 lg:py-6"
      >
        <div className="mx-auto w-full max-w-[1300px]">
          {children}
        </div>
      </motion.main>
    </>
  )
}
