'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { fetchWithTimeout } from '@/lib/fetch'
import { Label } from './Reveal'

interface Stats {
  active_students: number
  quizzes_completed: number
  lesson_plans_generated: number
  knowledge_assets: number
  system_status: string
}

/**
 * "Platform numbers" — live counts from `GET /auth/public-stats`. There are
 * no fabricated fallbacks: while loading, each figure is a pulsing skeleton;
 * if the endpoint fails, each figure renders an em dash (the old hardcoded
 * defaults were removed deliberately — no invented statistics).
 */
export default function StatsSection() {
  const t = useTranslations('landing')
  const [stats, setStats] = useState<Stats | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchWithTimeout('/auth/public-stats')
      .then((data) => {
        if (cancelled) return
        if (data && data.active_students) setStats(data)
        else setFailed(true)
      })
      .catch((err) => {
        if (cancelled) return
        console.log('Stats fetch error: showing no counts', err)
        setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const cells: Array<{ value: number | null; labelKey: string }> = [
    { value: stats?.active_students ?? null, labelKey: 'stats_students' },
    { value: stats?.quizzes_completed ?? null, labelKey: 'stats_quizzes' },
    { value: stats?.lesson_plans_generated ?? null, labelKey: 'stats_lessons' },
    { value: stats?.knowledge_assets ?? null, labelKey: 'stats_assets' },
  ]

  return (
    <section
      id="stats"
      className="border-t"
      aria-busy={!stats && !failed}
      aria-label={t('stats_aria')}
    >
      <div className="mx-auto max-w-[1280px] px-5 py-24 md:px-8">
        <div className="mb-16">
          <Label>{t('stats_kicker')}</Label>
          <h2 className="display mt-6 text-[40px] text-white md:text-[56px]">{t('stats_title')}</h2>
          {/* live badge only once counts are actually in — never on failure */}
          {stats && (
            <div className="mt-4 inline-flex items-center space-x-2 border border-mint/30 bg-mint/10 px-3 py-1">
              <span
                className="h-1.5 w-1.5 animate-ping rounded-full bg-mint motion-reduce:animate-none"
                aria-hidden
              />
              <span className="label-mono text-mint">{t('stats_badge')}</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-8 lg:grid-cols-4">
          {cells.map((cell) => (
            <div
              key={cell.labelKey}
              className="rounded-card border border-line bg-slate p-6 text-center"
            >
              <span className="display mb-2 block text-3xl font-black tabular-nums text-white sm:text-5xl">
                {cell.value != null ? (
                  cell.value.toLocaleString()
                ) : failed ? (
                  <span aria-hidden>—</span>
                ) : (
                  <span
                    className="inline-block h-9 w-24 animate-pulse bg-ink align-middle motion-reduce:animate-none"
                    aria-hidden
                  />
                )}
              </span>
              <span className="label-mono block text-meta">{t(cell.labelKey)}</span>
            </div>
          ))}
        </div>
        {failed && (
          <p className="mt-6 text-center text-sm text-meta">{t('stats_error')}</p>
        )}
      </div>
    </section>
  )
}
