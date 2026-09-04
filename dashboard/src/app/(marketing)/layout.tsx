'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import { getToken } from '@/lib/auth'
import LanguageSwitcher from '@/components/LanguageSwitcher'

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const t = useTranslations('landing')
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  useEffect(() => {
    setIsLoggedIn(!!getToken())
  }, [])

  return (
    <div className="bg-[#131313] text-white min-h-screen flex flex-col font-sans selection:bg-[#3cffd0] selection:text-black">
      {/* Navigation Header */}
      <header className="border-b border-[#2d2d2d] sticky top-0 bg-[#131313]/90 backdrop-blur-md z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center">
              <span className="verge-display text-2xl font-black tracking-tighter text-white hover:text-[#3cffd0] transition-colors">
                EthioSci
              </span>
            </Link>
            <nav className="hidden md:flex space-x-6">
              <a href="#features" className="verge-label text-gray-400 hover:text-white transition-colors">{t('nav_features')}</a>
              <a href="#console" className="verge-label text-gray-400 hover:text-white transition-colors">{t('nav_demo')}</a>
              <a href="#stats" className="verge-label text-gray-400 hover:text-white transition-colors">{t('nav_numbers')}</a>
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            {/* Language Switcher */}
            <LanguageSwitcher
              variant="toggle"
              className="flex bg-[#222222] border border-[#333333] p-0.5 rounded-sm"
            />

            {/* Launch App / Dashboard button */}
            <Link 
              href={isLoggedIn ? '/v2/overview' : '/login'} 
              className="bg-[#3cffd0] hover:bg-[#2be0b5] text-black font-mono font-bold text-xs uppercase tracking-wider px-4 py-2 rounded-none border border-black hover:translate-x-[-2px] hover:translate-y-[-2px] transition-all hover:shadow-[2px_2px_0px_0px_#5200ff]"
            >
              {t('cta_app')}
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#2d2d2d] bg-[#0c0c0c] py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <span className="verge-display text-xl font-bold text-white">EthioSci</span>
              <p className="mt-4 text-sm text-gray-500 max-w-xs leading-relaxed">
                {t('footer_tagline')}
              </p>
            </div>
            <div>
              <h4 className="verge-label text-sm text-white mb-4">{t('footer_resources')}</h4>
              <ul className="space-y-2 text-sm text-gray-400 font-mono">
                <li><a href="#features" className="hover:text-[#3cffd0]">{t('section_features')}</a></li>
                <li><a href="#console" className="hover:text-[#3cffd0]">{t('console_title')}</a></li>
                <li><a href="https://t.me/ethiobio_bot" target="_blank" rel="noopener noreferrer" className="hover:text-[#3cffd0]">Telegram Bot</a></li>
              </ul>
            </div>
            <div>
              <h4 className="verge-label text-sm text-white mb-4">{t('footer_portal')}</h4>
              <ul className="space-y-2 text-sm text-gray-400 font-mono">
                <li><Link href="/login" className="hover:text-[#3cffd0]">Login / Verify OTP</Link></li>
                <li><Link href="/v2/overview" className="hover:text-[#3cffd0]">Teacher Workspace</Link></li>
                <li><Link href="/student" className="hover:text-[#3cffd0]">Student Center</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-[#1e1e1e] mt-12 pt-8 flex flex-col md:flex-row items-center justify-between">
            <span className="text-xs font-mono text-gray-600">
              &copy; {new Date().getFullYear()} EthioSci. Inspired by brutalist digital design.
            </span>
          </div>
        </div>
      </footer>
    </div>
  )
}
