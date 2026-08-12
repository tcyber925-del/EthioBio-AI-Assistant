'use client'

import { useEffect, useState } from 'react'
import { useLocale, useTranslations } from 'next-intl'
import { Zap, FileCheck, MessageSquare, Medal } from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'
import { CardSkeleton } from '@/components/Skeleton'
import { ErrorBanner } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

interface ActivityItem {
  activity_type: string
  title: string
  description: string
  icon: string
  timestamp: string
}

const ICON_MAP: Record<string, { icon: typeof Zap; color: string }> = {
  xp_event: { icon: Zap, color: 'text-yellow-400 bg-yellow-500/10' },
  quiz_attempt: { icon: FileCheck, color: 'text-green-400 bg-green-500/10' },
  tutor_session: { icon: MessageSquare, color: 'text-blue-400 bg-blue-500/10' },
  achievement: { icon: Medal, color: 'text-purple-400 bg-purple-500/10' },
}

const DEFAULT_ICON = { icon: Zap, color: 'text-foreground-muted bg-border/50' }

function timeAgo(ts: string, t: (key: string, params?: any) => string, locale?: string): string {
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return t('just_now')
  if (mins < 60) return t('minutes_ago', { m: mins })
  const hours = Math.floor(mins / 60)
  if (hours < 24) return t('hours_ago', { h: hours })
  const days = Math.floor(hours / 24)
  if (days < 7) return t('days_ago', { d: days })
  return new Date(ts).toLocaleDateString(locale)
}

export default function ActivityFeed({ userId }: { userId: string }) {
  const locale = useLocale()
  const tc = useTranslations('common')
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)

  const fetchFeed = async () => {
    setLoading(true)
    try {
      const d = await fetchWithTimeout(`/api/activity/${userId}`)
      setActivities(d.activities || [])
      setError(null)
    } catch (err: unknown) {
      setError(normalizeException(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchFeed() }, [userId])

  if (loading) return <CardSkeleton />

  if (error) {
    return <ErrorBanner error={error} onAction={fetchFeed} />
  }

  if (activities.length === 0) {
    return (
      <div className="bg-card rounded-xl border border-border p-5 text-center">
        <MessageSquare className="w-8 h-8 text-border mx-auto mb-2" />
        <p className="text-sm text-foreground-muted font-medium">{tc('no_recent_activity')}</p>
        <p className="text-xs text-foreground-muted/60 mt-1">{tc('activity_desc')}</p>
      </div>
    )
  }

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <h3 className="text-sm font-semibold text-foreground mb-4">{tc('recent_activity')}</h3>
      <div className="space-y-3">
        {activities.map((a, i) => {
          const cfg = ICON_MAP[a.activity_type] || DEFAULT_ICON
          const Icon = cfg.icon
          return (
            <div key={`${a.activity_type}-${i}`} className="flex items-start gap-3">
              <div className={`p-1.5 rounded-lg ${cfg.color} shrink-0`}>
                <Icon className="w-3.5 h-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-foreground truncate">{a.title}</p>
                <p className="text-[11px] text-foreground-muted truncate">{a.description}</p>
                <p className="text-[10px] text-foreground-muted/60 mt-0.5">{timeAgo(a.timestamp, tc, locale)}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
