'use client'

import dynamic from 'next/dynamic'

function ConsoleSkeleton() {
  return (
    <section
      aria-busy="true"
      aria-label="Interactive demo loading"
      className="border-b border-[#2d2d2d] py-20"
    >
      <div className="mx-auto max-w-7xl animate-pulse px-4 sm:px-6 lg:px-8">
        <div className="mx-auto mb-12 h-8 w-64 bg-[#2d2d2d]" />
        <div className="h-[420px] border border-[#2d2d2d] bg-[#181818]" />
      </div>
    </section>
  )
}

function StatsSkeleton() {
  return (
    <section aria-busy="true" aria-label="Platform numbers loading" className="bg-[#1c1c1c] py-20">
      <div className="mx-auto max-w-7xl animate-pulse px-4 sm:px-6 lg:px-8">
        <div className="mx-auto mb-16 h-8 w-48 bg-[#2d2d2d]" />
        <div className="grid grid-cols-2 gap-8 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="h-28 border border-[#2d2d2d] bg-[#131313]" />
          ))}
        </div>
      </div>
    </section>
  )
}

export const LazyConsoleTabs = dynamic(() => import('./ConsoleTabs'), {
  ssr: false,
  loading: () => <ConsoleSkeleton />,
})

export const LazyStatsSection = dynamic(() => import('./StatsSection'), {
  ssr: false,
  loading: () => <StatsSkeleton />,
})