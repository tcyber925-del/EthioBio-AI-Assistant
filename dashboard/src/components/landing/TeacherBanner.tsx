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
    <div className="border-b border-[#2d2d2d] bg-[#1a1a1a]">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-2 sm:px-6 lg:px-8">
        <p className="text-xs text-gray-400 font-sans">
          {t('banner_teacher')}{' '}
          <Link
            href="/sign-up?role=teacher"
            className="font-bold text-[#3cffd0] hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0]"
          >
            {t('banner_signup_free')}
          </Link>
        </p>
        <button
          type="button"
          onClick={dismiss}
          aria-label={t('banner_dismiss')}
          className="shrink-0 p-1 text-gray-500 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0]"
        >
          <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>
    </div>
  )
}