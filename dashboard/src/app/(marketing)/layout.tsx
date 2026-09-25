'use client'

import { useEffect, useState } from 'react'
import { MotionConfig } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import { getToken } from '@/lib/auth'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import TeacherBanner from '@/components/landing/TeacherBanner'

/**
 * `(marketing)` shell: the generated design's sticky nav (compact on scroll,
 * hamburger under md) with this repo's kept chrome — TeacherBanner above,
 * LanguageSwitcher and the auth-aware header CTA inside the nav, full footer
 * below. `mk-surface` (globals.css) applies the marketing type stack, hairline
 * default borders, mint focus ring and dark browser chrome; `MotionConfig`
 * gives every reveal `reducedMotion="user"`.
 */
const navLinks = [
  { href: '#learn', labelKey: 'nav_learn' },
  { href: '#subjects', labelKey: 'nav_subjects' },
  { href: '#how', labelKey: 'nav_how' },
  { href: '#teachers', labelKey: 'nav_teachers' },
] as const

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations('landing')
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [compact, setCompact] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    setIsLoggedIn(!!getToken())
  }, [])

  useEffect(() => {
    const onScroll = () => setCompact(window.scrollY > 40)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="mk-surface flex min-h-screen flex-col bg-ink text-white selection:bg-mint selection:text-ink">
      <TeacherBanner />

      <header
        className={`sticky top-0 z-50 border-b bg-ink/95 backdrop-blur-md transition-[padding] duration-300 ${
          compact ? 'py-2' : 'py-5'
        }`}
      >
        <nav
          aria-label={t('nav_aria_main')}
          className="mx-auto flex max-w-[1280px] items-center justify-between gap-6 px-5 md:px-8"
        >
          <a href="#top" className="display text-2xl tracking-wide text-white">
            Ethio<span className="text-mint">Sci</span>
          </a>

          <ul className="hidden items-center gap-8 md:flex">
            {navLinks.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="label-mono text-soft transition-colors hover:text-mint"
                >
                  {t(link.labelKey)}
                </a>
              </li>
            ))}
          </ul>

          <div className="flex items-center gap-2">
            <LanguageSwitcher
              variant="toggle"
              className="hidden rounded-input border border-line bg-slate p-0.5 md:flex"
            />

            <Link
              href={isLoggedIn ? '/v2/overview' : '/login'}
              className="label-mono inline-flex min-h-11 items-center whitespace-nowrap rounded-cta bg-mint px-5 font-bold text-ink transition-colors hover:bg-white"
            >
              {t('cta_app')}
            </Link>

            <button
              type="button"
              className="inline-flex size-11 items-center justify-center rounded-full border md:hidden"
              aria-expanded={open}
              aria-controls="mobile-menu"
              aria-label={open ? t('nav_menu_close') : t('nav_menu_open')}
              onClick={() => setOpen((o) => !o)}
            >
              {open ? (
                <X className="h-5 w-5" aria-hidden />
              ) : (
                <Menu className="h-5 w-5" aria-hidden />
              )}
            </button>
          </div>
        </nav>

        {open && (
          <div id="mobile-menu" className="mx-5 mt-3 border-t md:hidden">
            <LanguageSwitcher
              variant="toggle"
              className="my-3 flex rounded-input border border-line bg-slate p-0.5"
            />
            <ul className="flex flex-col">
              {navLinks.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className="label-mono flex min-h-12 items-center border-b text-soft"
                  >
                    {t(link.labelKey)}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </header>

      <main className="flex-grow">
        <MotionConfig reducedMotion="user">
          {children}
        </MotionConfig>
      </main>

      <footer className="border-t border-slate bg-ink py-12">
        <div className="mx-auto max-w-[1280px] px-5 md:px-8">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
            <div>
              <span className="display text-xl text-white">
                Ethio<span className="text-mint">Sci</span>
              </span>
              <p className="mt-4 max-w-xs text-sm leading-relaxed text-meta">
                {t('footer_tagline')}
              </p>
            </div>
            <div>
              <h4 className="label-mono mb-4 text-white">{t('footer_resources')}</h4>
              <ul className="space-y-2 font-mono text-sm text-soft">
                <li>
                  <a href="#learn" className="hover:text-mint">
                    {t('nav_learn')}
                  </a>
                </li>
                <li>
                  <a href="#subjects" className="hover:text-mint">
                    {t('nav_subjects')}
                  </a>
                </li>
                <li>
                  <a href="#faq" className="hover:text-mint">
                    {t('faq_nav')}
                  </a>
                </li>
                <li>
                  <a
                    href="https://t.me/ethiobio_bot"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-mint"
                  >
                    {t('footer_telegram')}
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="label-mono mb-4 text-white">{t('footer_portal')}</h4>
              <ul className="space-y-2 font-mono text-sm text-soft">
                <li>
                  <Link href="/login" className="hover:text-mint">
                    {t('footer_login')}
                  </Link>
                </li>
                <li>
                  <Link href="/v2/overview" className="hover:text-mint">
                    {t('footer_workspace')}
                  </Link>
                </li>
                <li>
                  <Link href="/student" className="hover:text-mint">
                    {t('footer_student')}
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="mt-12 flex flex-col items-center justify-between border-t border-line pt-8 md:flex-row">
            <span className="font-mono text-xs text-meta">
              {t('footer_copyright', { year: new Date().getFullYear() })}
            </span>
          </div>
        </div>
      </footer>
    </div>
  )
}
