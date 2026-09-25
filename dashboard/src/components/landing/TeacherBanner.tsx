'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { X } from 'lucide-react'

const DISMISS_KEY = 'ethiosci_banner_teacher_dismissed'

export default function TeacherBanner() {
  const t = useTranslations('landing')
  const [dismissed, setDismissed] = useState(true)

  useEffect(() => {
    try {
      setDismissed(localStorage.getItem(DISMISS_KEY) === '1')
    } catch {
      setDismissed(false)
    }
  }, [])

  if (dismissed) return null

  const dismiss = () => {
    setDismissed(true)
    try {
      localStorage.setItem(DISMISS_KEY, '1')
    } catch {
      // storage unavailable — banner just stays for the session
    }
  }

  return (
    <div className="border-b border-slate bg-ink">
      <div className="mx-auto flex max-w-[1280px] items-center justify-between gap-4 px-5 py-2 md:px-8">
        <p className="text-xs text-soft">
          {t('banner_teacher')}{' '}
          <Link
            href="/sign-up?role=teacher"
            className="font-bold text-mint transition-colors hover:text-white"
          >
            {t('banner_signup_free')}
          </Link>
        </p>
        <button
          type="button"
          onClick={dismiss}
          aria-label={t('banner_dismiss')}
          className="shrink-0 p-1 text-meta transition-colors hover:text-white"
        >
          <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>
    </div>
  )
}