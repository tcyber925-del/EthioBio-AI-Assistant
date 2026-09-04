'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useClerk } from '@clerk/nextjs'

export default function SSOCallbackPage() {
  const clerk = useClerk()
  const router = useRouter()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const fallback = params.get('redirect_url') || '/v2/overview'
    const timeout = setTimeout(() => router.push(fallback), 12000)
    clerk
      .handleRedirectCallback({}, async (url) => {
        router.push(url || fallback)
      })
      .catch(() => router.push('/sign-in'))
    return () => clearTimeout(timeout)
  }, [clerk, router])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <p className="text-sm text-foreground-muted">Redirecting…</p>
    </div>
  )
}