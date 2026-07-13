'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { getToken } from '@/lib/auth'

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const t = useTranslations('landing')
  const router = useRouter()
  const pathname = usePathname()
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [locale, setLocale] = useState('en')

  useEffect(() => {
    setIsLoggedIn(!!getToken())
    
    // Read locale from cookie
    const match = document.cookie.match(new RegExp('(^| )NEXT_LOCALE=([^;]*)'))
    if (match) {
      setLocale(match[2])
    }
  }, [])

  const handleLanguageChange = (newLocale: string) => {
    document.cookie = `NEXT_LOCALE=${newLocale}; path=/; max-age=31536000; SameSite=Lax`
    setLocale(newLocale)
    router.refresh()
  }

  return (
    <div className="bg-[#131313] text-white min-h-screen flex flex-col font-sans selection:bg-[#3cffd0] selection:text-black">
      {/* Navigation Header */}
      <header className="border-b border-[#2d2d2d] sticky top-0 bg-[#131313]/90 backdrop-blur-md z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center">
              <span className="verge-display text-2xl font-black tracking-tighter text-white hover:text-[#3cffd0] transition-colors">
                EthioBio <span className="text-[#3cffd0]">AI</span>
              </span>
            </Link>
            <nav className="hidden md:flex space-x-6">
              <a href="#features" className="verge-label text-gray-400 hover:text-white transition-colors">Features</a>
              <a href="#console" className="verge-label text-gray-400 hover:text-white transition-colors">Interactive Demo</a>
              <a href="#stats" className="verge-label text-gray-400 hover:text-white transition-colors">Numbers</a>
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            {/* Language Switcher */}
            <div className="flex bg-[#222222] border border-[#333333] p-0.5 rounded-sm">
              <button 
                onClick={() => handleLanguageChange('en')}
                className={`px-2.5 py-1 text-xs font-mono rounded-sm transition-all ${locale === 'en' ? 'bg-[#3cffd0] text-black font-bold' : 'text-gray-400 hover:text-white'}`}
              >
                EN
              </button>
              <button 
                onClick={() => handleLanguageChange('am')}
                className={`px-2.5 py-1 text-xs font-mono rounded-sm transition-all ${locale === 'am' ? 'bg-[#3cffd0] text-black font-bold' : 'text-gray-400 hover:text-white'}`}
              >
                አማ
              </button>
            </div>

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
              <span className="verge-display text-xl font-bold text-white">EthioBio AI</span>
              <p className="mt-4 text-sm text-gray-500 max-w-xs leading-relaxed">
                Empowering secondary biology students and teachers across Ethiopia with textbook-grounded AI intelligence.
              </p>
            </div>
            <div>
              <h4 className="verge-label text-sm text-white mb-4">Resources</h4>
              <ul className="space-y-2 text-sm text-gray-400 font-mono">
                <li><a href="#features" className="hover:text-[#3cffd0]">Core Modules</a></li>
                <li><a href="#console" className="hover:text-[#3cffd0]">Product Console</a></li>
                <li><a href="https://t.me/ethiobio_bot" target="_blank" rel="noopener noreferrer" className="hover:text-[#3cffd0]">Telegram Bot</a></li>
              </ul>
            </div>
            <div>
              <h4 className="verge-label text-sm text-white mb-4">Portal</h4>
              <ul className="space-y-2 text-sm text-gray-400 font-mono">
                <li><Link href="/login" className="hover:text-[#3cffd0]">Login / Verify OTP</Link></li>
                <li><Link href="/v2/overview" className="hover:text-[#3cffd0]">Teacher Workspace</Link></li>
                <li><Link href="/student" className="hover:text-[#3cffd0]">Student Center</Link></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-[#1e1e1e] mt-12 pt-8 flex flex-col md:flex-row items-center justify-between">
            <span className="text-xs font-mono text-gray-600">
              &copy; {new Date().getFullYear()} EthioBio AI Assistant. Inspired by brutalist digital design.
            </span>
            <div className="flex space-x-4 mt-4 md:mt-0 text-xs font-mono text-gray-500">
              <span className="text-[#3cffd0]">● System status: healthy</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
