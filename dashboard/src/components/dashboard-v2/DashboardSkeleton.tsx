'use client'

import { motion } from 'framer-motion'

export function DashboardSkeleton() {
  return (
    <div className="flex h-screen overflow-hidden bg-v2-bg">
      <div className="w-64 shrink-0 bg-v2-surface border-r border-v2-border p-4 space-y-4">
        <div className="h-8 w-32 bg-v2-border/50 rounded-lg animate-pulse" />
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-10 bg-v2-border/30 rounded-xl animate-pulse" style={{ animationDelay: `${i * 50}ms` }} />
          ))}
        </div>
      </div>
      <div className="flex-1 p-10 space-y-6">
        <div className="h-10 w-48 bg-v2-border/30 rounded-lg animate-pulse" />
        <div className="h-6 w-96 bg-v2-border/20 rounded-lg animate-pulse" />
        <div className="grid grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 bg-v2-surface rounded-[20px] border border-v2-border animate-pulse" style={{ animationDelay: `${i * 80}ms` }} />
          ))}
        </div>
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-6">
            <div className="h-48 bg-v2-surface rounded-[20px] border border-v2-border animate-pulse" />
            <div className="h-64 bg-v2-surface rounded-[20px] border border-v2-border animate-pulse" />
          </div>
          <div className="space-y-6">
            <div className="h-48 bg-v2-surface rounded-[20px] border border-v2-border animate-pulse" />
            <div className="h-48 bg-v2-surface rounded-[20px] border border-v2-border animate-pulse" />
          </div>
        </div>
      </div>
    </div>
  )
}
