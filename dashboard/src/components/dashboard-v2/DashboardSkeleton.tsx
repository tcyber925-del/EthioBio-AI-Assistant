'use client'

export function DashboardSkeleton() {
  return (
    <div className="flex h-screen overflow-hidden bg-v2-bg text-v2-text-primary">
      <div className="w-64 shrink-0 border-r border-v2-border bg-v2-bg p-4 space-y-4">
        <div className="h-12 w-36 rounded-[20px] border border-v2-border bg-v2-surface animate-pulse" />
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-10 rounded-[20px] border border-v2-border bg-v2-surface animate-pulse" style={{ animationDelay: `${i * 50}ms` }} />
          ))}
        </div>
      </div>
      <div className="flex-1 p-6 sm:p-10 space-y-6">
        <div className="h-14 w-64 rounded-[24px] border border-v2-border bg-v2-surface animate-pulse" />
        <div className="h-5 w-full max-w-md rounded-[20px] bg-v2-surface animate-pulse" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 rounded-[20px] border border-v2-border bg-v2-surface animate-pulse" style={{ animationDelay: `${i * 80}ms` }} />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <div className="h-48 rounded-[20px] border border-v2-border bg-v2-surface animate-pulse" />
            <div className="h-64 rounded-[20px] border border-v2-border bg-v2-surface animate-pulse" />
          </div>
          <div className="space-y-6">
            <div className="h-48 rounded-[20px] border border-v2-border bg-v2-surface animate-pulse" />
            <div className="h-48 rounded-[20px] border border-v2-border bg-v2-surface animate-pulse" />
          </div>
        </div>
      </div>
    </div>
  )
}
