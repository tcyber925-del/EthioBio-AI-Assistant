'use client'

import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { SidebarV2 } from './SidebarV2'
import { ContextHeader } from './ContextHeader'
import { BioPattern } from './BioPattern'

interface DashboardLayoutProps {
  children: ReactNode
  breadcrumbs: { label: string; href?: string }[]
}

export function DashboardLayout({ children, breadcrumbs }: DashboardLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-v2-bg">
      <SidebarV2 />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <BioPattern />
        <header className="relative z-10 shrink-0 px-10 pt-6 pb-0">
          <ContextHeader items={breadcrumbs} />
        </header>
        <motion.main
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="relative z-10 flex-1 overflow-y-auto px-10 py-6"
        >
          {children}
        </motion.main>
      </div>
    </div>
  )
}
