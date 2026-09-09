'use client'

import Link from 'next/link'
import { useTranslations } from 'next-intl'
import LanguageSwitcher from '@/components/LanguageSwitcher'

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const tCommon = useTranslations('common')
  const tLogin = useTranslations('login')

  return (
    <div className="flex min-h-screen flex-col bg-v2-bg text-v2-text-primary">
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-10">
        <div className="mb-6 flex w-full max-w-[440px] items-center justify-between">
          <Link
            href="/"
            className="text-display text-xl font-bold tracking-tight text-v2-text-primary no-underline"
          >
            {tLogin('brand_short')}
          </Link>
          <LanguageSwitcher
            variant="select"
            className="rounded-lg border border-v2-border bg-v2-surface px-2 py-1.5 text-sm text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
          />
        </div>

        <div className="w-full max-w-[440px] rounded-2xl border border-v2-border bg-v2-surface p-6 shadow-sm sm:p-8">
          {children}
        </div>

        <footer className="mt-6 flex w-full max-w-[440px] items-center justify-center gap-4 text-xs text-v2-text-secondary">
          <Link
            href="/terms"
            className="hover:text-v2-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
          >
            {tCommon('terms_of_service')}
          </Link>
          <span aria-hidden>·</span>
          <Link
            href="/privacy"
            className="hover:text-v2-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
          >
            {tCommon('privacy_policy')}
          </Link>
        </footer>
      </div>
    </div>
  )
}
