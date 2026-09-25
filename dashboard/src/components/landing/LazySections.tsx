'use client'

import dynamic from 'next/dynamic'
import { useTranslations } from 'next-intl'

/**
 * Heavy interactive sections load lazily with a skeleton in place
 * (the pattern the old ConsoleTabs used): the ask-demo typing panel, the
 * quiz card, and the stats band that fetches `/auth/public-stats`.
 */

function DemoSkeleton() {
  const t = useTranslations('landing')
  return (
    <section aria-busy="true" aria-label={t('loading_demo')} className="border-t">
      <div className="mx-auto grid max-w-[1280px] animate-pulse gap-12 px-5 py-24 md:px-8 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <div className="h-4 w-40 bg-slate" />
          <div className="mt-6 h-14 w-full bg-slate" />
        </div>
        <div className="min-h-[420px] rounded-feature border bg-slate lg:col-span-8" />
      </div>
    </section>
  )
}

function QuizSkeleton() {
  const t = useTranslations('landing')
  return (
    <section aria-busy="true" aria-label={t('loading_quiz')} className="border-t bg-violet">
      <div className="mx-auto grid max-w-[1280px] animate-pulse gap-12 px-5 py-24 md:px-8 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <div className="h-4 w-32 bg-ink/40" />
          <div className="mt-6 h-14 w-full bg-ink/40" />
        </div>
        <div className="min-h-[420px] rounded-feature bg-ink lg:col-span-7" />
      </div>
    </section>
  )
}

function StatsSkeleton() {
  const t = useTranslations('landing')
  return (
    <section aria-busy="true" aria-label={t('loading_stats')} className="border-t">
      <div className="mx-auto max-w-[1280px] animate-pulse px-5 py-24 md:px-8">
        <div className="mb-16 text-center">
          <div className="mx-auto h-10 w-64 bg-slate" />
        </div>
        <div className="grid grid-cols-2 gap-8 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="h-28 border border-line bg-slate" />
          ))}
        </div>
      </div>
    </section>
  )
}

export const LazyAskDemo = dynamic(() => import('./AskDemoSection'), {
  ssr: false,
  loading: () => <DemoSkeleton />,
})

export const LazyQuizDemo = dynamic(() => import('./QuizDemoSection'), {
  ssr: false,
  loading: () => <QuizSkeleton />,
})

export const LazyStatsSection = dynamic(() => import('./StatsSection'), {
  ssr: false,
  loading: () => <StatsSkeleton />,
})
