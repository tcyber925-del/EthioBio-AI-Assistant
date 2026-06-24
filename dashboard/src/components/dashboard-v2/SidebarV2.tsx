'use client'

import { useState, useCallback, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  ChevronLeft,
  Search,
  LogOut,
  Globe,
  Bot,
  Brain,
  ClipboardCheck,
  Activity,
  BarChart3,
  GraduationCap,
  UserCheck,
} from 'lucide-react'
import { DnaIcon } from './BioIcon'
import { useTranslations } from 'next-intl'
import { useLocale } from 'next-intl'
import { clearToken, getUserRole, isAuthenticated } from '@/lib/auth'
import { setCookie } from '@/lib/cookies'

interface NavSection {
  section: string | null
  items: NavItem[]
}

interface NavItem {
  label: string
  href: string
  icon: React.ElementType
  roles: string[]
}

const NAV_STRUCTURE: NavSection[] = [
  {
    section: null,
    items: [
      { label: 'Overview', href: '/v2/overview', icon: LayoutDashboard, roles: ['admin', 'teacher', 'student', 'parent', 'school'] },
      { label: 'Copilot', href: '/copilot', icon: Bot, roles: ['admin', 'teacher'] },
      { label: 'Assessments', href: '/assessment-studio', icon: ClipboardCheck, roles: ['admin', 'teacher'] },
      { label: 'Interventions', href: '/interventions', icon: Activity, roles: ['admin', 'teacher'] },
      { label: 'Analytics',     href: '/intervention-analytics', icon: BarChart3,  roles: ['admin', 'teacher'] },
      { label: 'Lesson Plans',  href: '/classroom-adaptations', icon: GraduationCap, roles: ['admin', 'teacher'] },
      { label: 'Misconceptions', href: '/misconceptions',   icon: Brain,           roles: ['admin', 'teacher'] },
      { label: 'Digital Twin', href: '/digital-twin', icon: UserCheck, roles: ['admin', 'teacher', 'student'] },
    ],
  },
]

export function SidebarV2() {
  const t = useTranslations('sidebar')
  const locale = useLocale()
  const pathname = usePathname()
  const router = useRouter()
  const [collapsed, setCollapsed] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const role = getUserRole()
  const authenticated = isAuthenticated()

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault()
        setCollapsed(prev => !prev)
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen(prev => !prev)
      }
      if (e.key === 'Escape') {
        setSearchOpen(false)
        setSearchQuery('')
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const isActive = useCallback((href: string) => {
    if (href === '/v2/overview') return pathname === '/v2/overview' || pathname === '/v2'
    return pathname.startsWith(href)
  }, [pathname])

  const handleLogout = () => {
    clearToken()
    router.push('/login')
  }

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLocale = e.target.value
    setCookie('NEXT_LOCALE', newLocale, 365)
    router.refresh()
  }

  if (!authenticated) return null

  const filteredNav = NAV_STRUCTURE.map(section => ({
    ...section,
    items: section.items.filter(item => !role || item.roles.includes(role)),
  })).filter(section => section.items.length > 0)

  const searchResults = searchQuery
    ? filteredNav.flatMap(s => s.items).filter(i =>
        i.label.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : []

  return (
    <>
      <motion.aside
        className="h-screen bg-v2-surface border-r border-v2-border flex flex-col flex-shrink-0 overflow-hidden relative z-30"
        animate={{ width: collapsed ? 72 : 256 }}
        transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      >
        {/* Subtle biology background */}
        <div className="absolute inset-0 pointer-events-none select-none opacity-[0.02]" aria-hidden="true">
          <svg width="100%" height="100%" className="text-v2-accent">
            <defs>
              <pattern id="sidebar-dots" x="0" y="0" width="32" height="32" patternUnits="userSpaceOnUse">
                <circle cx="16" cy="16" r="0.8" fill="currentColor" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#sidebar-dots)" />
          </svg>
        </div>

        {/* Logo area */}
        <div className="flex items-center justify-between px-4 h-16 border-b border-v2-border">
          <AnimatePresence mode="wait">
            {!collapsed ? (
              <motion.div
                key="expanded-logo"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-3 overflow-hidden"
              >
                <div className="w-8 h-8 rounded-lg bg-v2-accent flex items-center justify-center text-white shrink-0">
                  <DnaIcon className="w-4.5 h-4.5" />
                </div>
                <div className="truncate">
                  <p className="text-sm font-semibold text-v2-text-primary">EthioBio</p>
                  <p className="text-[11px] text-v2-text-secondary">AI Assistant</p>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="collapsed-logo"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="w-8 h-8 rounded-lg bg-v2-accent flex items-center justify-center text-white mx-auto"
              >
                <DnaIcon className="w-4.5 h-4.5" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Search trigger */}
        <button
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-3 mx-3 mt-3 px-3 h-9 rounded-lg border border-v2-border text-v2-text-secondary text-sm hover:bg-v2-bg transition-colors duration-150"
        >
          <Search className="w-4 h-4 shrink-0" />
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                key="search-text"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex-1 text-left"
              >
                Search
                <span className="ml-auto text-[11px] text-v2-text-secondary/50">⌘K</span>
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {filteredNav.map((section, i) => (
            <div key={i}>
              <AnimatePresence mode="wait">
                {!collapsed && section.section && (
                  <motion.p
                    key={`label-${i}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-[11px] font-semibold uppercase tracking-widest text-v2-text-secondary/60 px-3 mb-2"
                  >
                    {section.section}
                  </motion.p>
                )}
              </AnimatePresence>
              <div className="space-y-1">
                {section.items.map(item => {
                  const Icon = item.icon
                  const active = isActive(item.href)
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`flex items-center gap-3 px-3 h-10 rounded-xl text-sm transition-all duration-150 relative ${
                        active
                          ? 'bg-v2-accent-muted text-v2-accent font-medium'
                          : 'text-v2-text-secondary hover:bg-v2-bg hover:text-v2-text-primary'
                      }`}
                      title={collapsed ? item.label : undefined}
                    >
                      <Icon className="w-5 h-5 shrink-0" />
                      <AnimatePresence mode="wait">
                        {!collapsed && (
                          <motion.span
                            key={`label-${item.href}`}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="truncate"
                          >
                            {item.label}
                          </motion.span>
                        )}
                      </AnimatePresence>
                      {active && (
                        <motion.div
                          layoutId="active-indicator"
                          className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-v2-accent"
                          transition={{ duration: 0.2 }}
                        />
                      )}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom area */}
        <div className="border-t border-v2-border p-3 space-y-1">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-v2-text-secondary">
            <Globe className="w-4 h-4 shrink-0" />
            <AnimatePresence mode="wait">
              {!collapsed && (
                <motion.select
                  key="lang-select"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  value={locale}
                  onChange={handleLanguageChange}
                  className="bg-transparent text-v2-text-primary text-sm outline-none cursor-pointer w-full"
                >
                  <option value="en">English</option>
                  <option value="am">አማርኛ</option>
                </motion.select>
              )}
            </AnimatePresence>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-v2-text-secondary hover:text-v2-error hover:bg-v2-error/5 w-full transition-colors duration-150"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            <AnimatePresence mode="wait">
              {!collapsed && (
                <motion.span
                  key="signout-text"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  Sign out
                </motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(prev => !prev)}
          className="absolute -right-3 top-20 w-6 h-6 rounded-full border border-v2-border bg-v2-surface flex items-center justify-center text-v2-text-secondary hover:text-v2-accent hover:border-v2-accent transition-colors duration-150 shadow-sm"
        >
          <ChevronLeft
            className={`w-3.5 h-3.5 transition-transform duration-200 ${
              collapsed ? 'rotate-180' : ''
            }`}
          />
        </button>
      </motion.aside>

      {/* Search overlay */}
      <AnimatePresence>
        {searchOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/20 backdrop-blur-sm"
            onClick={() => { setSearchOpen(false); setSearchQuery('') }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: -10 }}
              transition={{ duration: 0.15 }}
              className="absolute top-[15%] left-1/2 -translate-x-1/2 w-full max-w-lg"
              onClick={e => e.stopPropagation()}
            >
              <div className="bg-v2-surface rounded-2xl shadow-xl border border-v2-border overflow-hidden">
                <div className="flex items-center gap-3 px-4 h-12 border-b border-v2-border">
                  <Search className="w-4 h-4 text-v2-text-secondary" />
                  <input
                    autoFocus
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search pages..."
                    className="flex-1 text-sm text-v2-text-primary bg-transparent outline-none placeholder:text-v2-text-secondary/50"
                  />
                  <kbd className="text-[11px] text-v2-text-secondary/50 bg-v2-bg px-1.5 py-0.5 rounded border border-v2-border">
                    ESC
                  </kbd>
                </div>
                {searchQuery && searchResults.length > 0 && (
                  <div className="p-2 space-y-0.5 max-h-64 overflow-y-auto">
                    {searchResults.map(item => {
                      const Icon = item.icon
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={() => { setSearchOpen(false); setSearchQuery('') }}
                          className="flex items-center gap-3 px-3 h-9 rounded-lg text-sm text-v2-text-secondary hover:bg-v2-bg hover:text-v2-text-primary transition-colors duration-150"
                        >
                          <Icon className="w-4 h-4 shrink-0" />
                          <span>{item.label}</span>
                        </Link>
                      )
                    })}
                  </div>
                )}
                {searchQuery && searchResults.length === 0 && (
                  <div className="p-8 text-center text-sm text-v2-text-secondary">
                    No results found for &quot;{searchQuery}&quot;
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
