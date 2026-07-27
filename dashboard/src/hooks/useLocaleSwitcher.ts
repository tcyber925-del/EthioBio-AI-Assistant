'use client'

import { useLocale } from 'next-intl'
import { useRouter } from 'next/navigation'
import { useCallback } from 'react'
import { getUserId } from '@/lib/auth'
import { setCookie } from '@/lib/cookies'
import { LOCALE_COOKIE, type Locale } from '@/lib/i18n-config'

/**
 * Single locale-switching path for the whole app: persist the choice in the
 * NEXT_LOCALE cookie, best-effort sync to the user's backend preference when
 * authenticated, then refresh server components so new messages load.
 */
export function useLocaleSwitcher() {
  const locale = useLocale() as Locale
  const router = useRouter()

  const switchLocale = useCallback(
    (next: Locale) => {
      if (next === locale) return
      setCookie(LOCALE_COOKIE, next, 365)
      const userId = getUserId()
      if (userId) {
        fetch(`/api/users/${userId}/language?language=${next}`, { method: 'PATCH' }).catch(() => {})
      }
      router.refresh()
    },
    [locale, router],
  )

  return { locale, switchLocale }
}
