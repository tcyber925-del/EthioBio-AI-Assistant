'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { useAuth, useClerk } from '@clerk/nextjs'
import { tryCompleteSignup } from '@/lib/auth/completeSignup'
import {
  resolvePostAuthDestinationOr,
  type PostAuthMe,
} from '@/lib/auth/resolveDestination'
import { fetchWithAuthJson } from '@/lib/fetchWithAuth'

export default function SsoCallbackPage() {
  const t = useTranslations('common')
  const router = useRouter()
  const clerk = useClerk()
  const { getToken } = useAuth()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const requestedNext = params.get('redirect_url')
    const watchdog = setTimeout(
      () => router.push(resolvePostAuthDestinationOr(null, null, requestedNext)),
      12000,
    )

    clerk
      .handleRedirectCallback({}, async () => {
        let me: PostAuthMe | null = null
        let failure: unknown = null
        try {
          me = await fetchWithAuthJson<PostAuthMe>('/auth/me')
        } catch (err) {
          failure = err
        }

        // New OAuth users carry a signed intent cookie — claim role/DOB now,
        // instead of bouncing back through the role picker.
        if (me && me.role_claimed === false) {
          me = (await tryCompleteSignup().catch(() => null)) ?? me
        }

        clearTimeout(watchdog)
        router.push(resolvePostAuthDestinationOr(me, failure, requestedNext))
      })
      .catch(() => {
        clearTimeout(watchdog)
        router.push('/login')
      })

    return () => clearTimeout(watchdog)
  }, [clerk, getToken, router])

  return (
    <div className="flex items-center justify-center py-8">
      <p className="text-sm text-v2-text-secondary">{t('loading')}</p>
    </div>
  )
}
