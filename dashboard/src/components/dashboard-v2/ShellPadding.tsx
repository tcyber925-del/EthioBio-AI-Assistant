'use client'

import { usePathname } from 'next/navigation'

export function ShellPadding({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isV2 = pathname === '/v2' || pathname.startsWith('/v2/')

  return (
    <div className={`relative z-10 flex-1 overflow-auto${isV2 ? '' : ' p-6 lg:p-8'}`}>
      {children}
    </div>
  )
}
