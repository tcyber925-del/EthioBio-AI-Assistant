'use client'

import { motion } from 'framer-motion'
import { Zap, FileCheck, MessageSquare, Medal, AlertTriangle } from 'lucide-react'

interface ActivityItem {
  type: string
  description: string
  created_at: string | null
}

interface ActivityTimelineProps {
  items: ActivityItem[]
}

const TIMELINE_ICONS: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  xp: { icon: Zap, color: 'text-v2-warning', bg: 'bg-v2-warning/10' },
  quiz: { icon: FileCheck, color: 'text-v2-success', bg: 'bg-v2-success/10' },
  tutor: { icon: MessageSquare, color: 'text-v2-accent', bg: 'bg-v2-accent-muted' },
  achievement: { icon: Medal, color: 'text-v2-accent', bg: 'bg-v2-accent-muted' },
}

const DEFAULT_ICON = { icon: AlertTriangle, color: 'text-v2-text-secondary', bg: 'bg-v2-border/50' }

function formatTime(ts: string | null): string {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(ts).toLocaleDateString()
}

export function ActivityTimeline({ items }: ActivityTimelineProps) {
  if (items.length === 0) return null

  return (
    <div>
      <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Recent Activity</h2>
      <div className="relative">
        <div className="absolute left-[17px] top-3 bottom-3 w-px bg-v2-border" />
        <div className="space-y-0">
          {items.slice(0, 10).map((item, i) => {
            const cfg = TIMELINE_ICONS[item.type] || DEFAULT_ICON
            const Icon = cfg.icon
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15, delay: i * 0.03 }}
                className="flex items-start gap-4 py-3 relative"
              >
                <div className={`relative z-10 p-1.5 rounded-lg ${cfg.bg} ${cfg.color} shrink-0`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0 pt-0.5">
                  <p className="text-sm text-v2-text-primary">{item.description}</p>
                  <p className="text-xs text-v2-text-secondary/60 mt-0.5">
                    {formatTime(item.created_at)}
                  </p>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
