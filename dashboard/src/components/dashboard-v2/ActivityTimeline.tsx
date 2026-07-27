'use client'

import { motion } from 'framer-motion'
import { Zap, FileCheck, MessageSquare, Medal, AlertTriangle } from 'lucide-react'
import { useTranslations } from 'next-intl'

interface ActivityItem {
  type: string
  description: string
  created_at: string | null
}

interface ActivityTimelineProps {
  items: ActivityItem[]
}

const TIMELINE_ICONS: Record<string, { icon: React.ElementType; accent: string; tile: string }> = {
  xp: { icon: Zap, accent: 'text-v2-warning', tile: 'border-v2-warning/70 bg-v2-bg' },
  quiz: { icon: FileCheck, accent: 'text-v2-accent', tile: 'border-v2-accent/70 bg-v2-surface' },
  tutor: { icon: MessageSquare, accent: 'text-v2-purple', tile: 'border-v2-purple/70 bg-v2-surface' },
  achievement: { icon: Medal, accent: 'text-v2-inverted', tile: 'border-v2-accent bg-v2-accent text-v2-inverted' },
}

const DEFAULT_ICON = { icon: AlertTriangle, accent: 'text-v2-text-secondary', tile: 'border-v2-border bg-v2-surface' }

const TYPE_LABEL_KEYS: Record<string, string> = {
  xp: 'type_xp',
  quiz: 'type_quiz',
  tutor: 'type_tutor',
  achievement: 'type_achievement',
}

type TFn = (key: string, values?: Record<string, string | number>) => string

function formatTime(ts: string | null, tc: TFn): string {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return tc('just_now')
  if (mins < 60) return tc('minutes_ago', { m: mins })
  const hours = Math.floor(mins / 60)
  if (hours < 24) return tc('hours_ago', { h: hours })
  const days = Math.floor(hours / 24)
  if (days < 7) return tc('days_ago', { d: days })
  return new Date(ts).toLocaleDateString()
}

export function ActivityTimeline({ items }: ActivityTimelineProps) {
  const t = useTranslations('v2.activity')
  const tc = useTranslations('common')
  if (items.length === 0) return null

  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-2xl font-black leading-none text-v2-text-primary">{t('title')}</h2>
        <span className="verge-label text-v2-accent">{t('storystream')}</span>
      </div>
      <div className="relative pl-12">
        <div className="absolute left-[25px] top-1 bottom-1 w-px bg-v2-purple-rule" />
        <div className="space-y-3">
          {items.slice(0, 10).map((item, i) => {
            const cfg = TIMELINE_ICONS[item.type] || DEFAULT_ICON
            const Icon = cfg.icon
            const isAccentTile = item.type === 'achievement'
            return (
              <motion.div
                key={`${item.type}-${item.description}-${item.created_at ?? i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15, delay: i * 0.03 }}
                className="relative"
              >
                <div className="absolute -left-12 top-5 flex w-10 justify-end pr-2">
                  <span className="verge-label whitespace-nowrap text-[10px] text-v2-text-secondary">
                    {formatTime(item.created_at, tc)}
                  </span>
                </div>
                <div className={`rounded-[20px] border p-4 transition-colors duration-150 hover:text-v2-link-hover ${cfg.tile}`}>
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${isAccentTile ? 'border-v2-inverted/30' : 'border-v2-border'} ${cfg.accent}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className={`verge-label mb-1 ${isAccentTile ? 'text-v2-inverted/70' : 'text-v2-text-secondary'}`}>{TYPE_LABEL_KEYS[item.type] ? t(TYPE_LABEL_KEYS[item.type]) : item.type}</p>
                      <p className={`text-sm leading-relaxed ${isAccentTile ? 'text-v2-inverted' : 'text-v2-text-primary'}`}>{item.description}</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
