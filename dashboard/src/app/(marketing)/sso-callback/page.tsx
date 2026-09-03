'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useClerk } from '@clerk/nextjs'

export default function SSOCallbackPage() {
  const clerk = useClerk()
  const router = useRouter()

  useEffect(() => {
    clerk
      .handleRedirectCallback({}, async (url) => {
        router.push(url);
      })
      .catch(() => router.push('/sign-in'))
  }, [clerk, router])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <p className="text-sm text-foreground-muted">Redirecting…</p>
    </div>
  )
}