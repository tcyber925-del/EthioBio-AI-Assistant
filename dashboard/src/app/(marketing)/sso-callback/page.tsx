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
        const me = await fetch('/auth/me', { credentials: 'include' })
          .then(r => (r.ok ? r.json() : null))
          .catch(() => null)
        const target = me && me.role_claimed === false ? '/login?role_claim=1' : (url || fallback)
        router.push(target)
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