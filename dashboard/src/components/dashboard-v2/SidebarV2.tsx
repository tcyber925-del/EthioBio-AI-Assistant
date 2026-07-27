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
  Home,
  School,
  Shield,
  User,
  Activity,
  ClipboardCheck,
  FileText,
  BookOpen,
  Users,
  BarChart3,
  MessageSquare,
  Cpu,
  GitFork,
  Upload,
} from 'lucide-react'
import { DnaIcon } from './BioIcon'
import LanguageSwitcher from '@/components/LanguageSwitcher'
import { useTranslations } from 'next-intl'
import { clearToken, getUserRole, isAuthenticated } from '@/lib/auth'

interface NavSection {
  sectionKey: string | null
  items: NavItem[]
}

interface NavItem {
  labelKey: string
  subtitleKey?: string
  href: string
  icon: React.ElementType
  roles: string[]
}

const NAV_STRUCTURE: NavSection[] = [
  {
    sectionKey: null,
    items: [
      { labelKey: 'overview', href: '/v2/overview', icon: LayoutDashboard, roles: ['admin', 'teacher', 'student', 'parent', 'school'] },
    ],
  },
  {
    sectionKey: 'section_main',
    items: [
      { labelKey: 'dashboard', href: '/dashboard', icon: Home, roles: ['admin'] },
      { labelKey: 'student_dashboard', href: '/student', icon: Home, roles: ['student'] },
      { labelKey: 'parent', href: '/parent', icon: User, roles: ['parent', 'admin'] },
    ],
  },
  {
    sectionKey: 'section_learning',
    items: [
      { labelKey: 'single_lesson', subtitleKey: 'single_lesson_sub', href: '/lessons', icon: FileText, roles: ['admin', 'teacher'] },
      { labelKey: 'unit_plan', subtitleKey: 'unit_plan_sub', href: '/unit-plans', icon: BookOpen, roles: ['admin', 'teacher'] },
      { labelKey: 'assessment_studio', href: '/assessment-studio', icon: ClipboardCheck, roles: ['admin', 'teacher'] },
      { labelKey: 'knowledge_graph', href: '/knowledge-graph', icon: GitFork, roles: ['admin', 'teacher'] },
      { labelKey: 'quizzes', href: '/quizzes', icon: ClipboardCheck, roles: ['admin', 'teacher'] },
      { labelKey: 'ask', href: '/ask', icon: MessageSquare, roles: ['admin', 'teacher', 'student', 'parent'] },
    ],
  },
  {
    sectionKey: 'section_management',
    items: [
      { labelKey: 'classroom', href: '/classroom', icon: School, roles: ['admin', 'teacher', 'student'] },
      { labelKey: 'students', href: '/students', icon: Users, roles: ['admin', 'teacher'] },
      { labelKey: 'school', href: '/school', icon: Shield, roles: ['admin'] },
      { labelKey: 'recovery', href: '/recovery', icon: Activity, roles: ['admin', 'teacher'] },
      { labelKey: 'interventions', href: '/intervention-analytics', icon: BarChart3, roles: ['admin', 'teacher'] },
    ],
  },
  {
    sectionKey: 'section_workspace',
    items: [
      { labelKey: 'dashboard', href: '/workspace', icon: LayoutDashboard, roles: ['admin', 'teacher'] },
      { labelKey: 'workspace_browse', href: '/workspace/browse', icon: BookOpen, roles: ['admin', 'teacher'] },
      { labelKey: 'workspace_upload', href: '/workspace/upload', icon: Upload, roles: ['admin', 'teacher'] },
      { labelKey: 'workspace_search', href: '/workspace/search', icon: Search, roles: ['admin', 'teacher'] },
      { labelKey: 'workspace_processing', href: '/workspace/processing', icon: Activity, roles: ['admin', 'teacher'] },
    ],
  },
  {
    sectionKey: 'section_system',
    items: [
      { labelKey: 'monitoring', href: '/monitoring', icon: BarChart3, roles: ['admin'] },
      { labelKey: 'diagrams', href: '/diagrams', icon: BarChart3, roles: ['admin', 'teacher', 'student', 'parent'] },
    ],
  },
  {
    sectionKey: 'section_admin',
    items: [
      { labelKey: 'admin_dashboard', href: '/admin', icon: Shield, roles: ['admin'] },
      { labelKey: 'review_queue', href: '/admin/review', icon: ClipboardCheck, roles: ['admin'] },
      { labelKey: 'content_review', href: '/admin/content', icon: FileText, roles: ['admin'] },
      { labelKey: 'schools', href: '/admin/schools', icon: School, roles: ['admin'] },
      { labelKey: 'users', href: '/admin/users', icon: Users, roles: ['admin'] },
      { labelKey: 'agents', href: '/admin/agents', icon: Cpu, roles: ['admin'] },
      { labelKey: 'monitoring', href: '/admin/monitoring', icon: BarChart3, roles: ['admin'] },
    ],
  },
]

export function SidebarV2() {
  const t = useTranslations('v2.nav')
  const ts = useTranslations('v2.sidebar')
  const pathname = usePathname()
  const router = useRouter()
  const [collapsed, setCollapsed] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [ready, setReady] = useState(false)
  const [role, setRole] = useState<string | null>(null)

  useEffect(() => {
    setRole(getUserRole())
    setReady(true)
  }, [])

  const authenticated = ready && isAuthenticated()

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
    if (href === '/') return pathname === '/'
  return pathname === href || pathname.startsWith(`${href}/`)
  }, [pathname])

  const handleLogout = () => {
    clearToken()
    router.push('/login')
  }

  if (!authenticated) return null

  const filteredNav = NAV_STRUCTURE.map(section => ({
    ...section,
    items: section.items.filter(item => !role || item.roles.includes(role)),
  })).filter(section => section.items.length > 0)

  const searchResults = searchQuery
    ? filteredNav.flatMap(s => s.items).filter(i =>
        t(i.labelKey).toLowerCase().includes(searchQuery.toLowerCase())
      )
    : []

  return (
    <>
      <motion.aside
        className="relative z-30 flex h-screen shrink-0 flex-col overflow-hidden border-r border-v2-border bg-v2-bg"
        animate={{ width: collapsed ? 72 : 256 }}
        transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="absolute inset-0 pointer-events-none select-none opacity-[0.04]" aria-hidden="true">
          <svg width="100%" height="100%" className="text-v2-accent">
            <defs>
              <pattern id="sidebar-hatch" x="0" y="0" width="28" height="28" patternUnits="userSpaceOnUse">
                <path d="M0 28L28 0" stroke="currentColor" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#sidebar-hatch)" />
          </svg>
        </div>

        <div className="relative flex h-20 items-center justify-between border-b border-v2-border px-4">
          <AnimatePresence mode="wait">
            {!collapsed ? (
              <motion.div
                key="expanded-logo"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="min-w-0 overflow-hidden"
              >
                <p className="verge-display truncate text-[32px] leading-none text-v2-text-primary">EthioBio</p>
                <p className="verge-label mt-1 text-v2-accent">{ts('brand_sub')}</p>
              </motion.div>
            ) : (
              <motion.div
                key="collapsed-logo"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="mx-auto flex h-10 w-10 items-center justify-center rounded-full border border-v2-accent text-v2-accent"
              >
                <DnaIcon className="h-5 w-5" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <button
          onClick={() => setSearchOpen(true)}
          aria-label={ts('open_search_aria')}
          className="relative mx-3 mt-4 flex h-10 items-center gap-3 rounded-[20px] border border-v2-border bg-v2-surface px-3 text-sm text-v2-text-secondary transition-colors duration-150 hover:border-v2-accent hover:text-v2-text-primary focus-visible:verge-focus"
        >
          <Search className="h-4 w-4 shrink-0" />
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                key="search-text"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-1 items-center justify-between gap-3 text-left"
              >
                <span className="verge-label">{ts('search')}</span>
                <span className="font-mono text-[10px] text-v2-text-secondary/70">CMD K</span>
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        <nav className="relative flex-1 overflow-y-auto px-3 py-5 space-y-6">
          {filteredNav.map((section, i) => (
            <div key={i}>
              <AnimatePresence mode="wait">
                {!collapsed && section.sectionKey && (
                  <motion.p
                    key={`label-${i}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="verge-label px-3 pb-2 text-v2-text-secondary"
                  >
                    {t(section.sectionKey)}
                  </motion.p>
                )}
              </AnimatePresence>
              <div className="space-y-2">
                {section.items.map(item => {
                  const Icon = item.icon
                  const active = isActive(item.href)
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`relative flex h-11 items-center gap-3 rounded-[20px] border px-3 text-sm transition-colors duration-150 focus-visible:verge-focus ${
                        active
                          ? 'border-v2-accent bg-v2-accent text-v2-inverted'
                          : 'border-v2-border bg-v2-bg text-v2-text-secondary hover:border-v2-accent hover:text-v2-link-hover'
                      }`}
                      title={collapsed ? t(item.labelKey) : undefined}
                    >
                      <Icon className="h-5 w-5 shrink-0" />
                      <AnimatePresence mode="wait">
                        {!collapsed && (
                          <motion.div
                            key={`label-${item.href}`}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="min-w-0"
                          >
                            <span className="verge-label truncate block">{t(item.labelKey)}</span>
                            {item.subtitleKey && (
                              <span className="text-[10px] text-v2-text-secondary/60 truncate block leading-tight">{t(item.subtitleKey)}</span>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
                      {active && <span className="absolute -left-3 top-1/2 h-7 w-px -translate-y-1/2 bg-v2-purple-rule" />}
                    </Link>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="relative border-t border-v2-border p-3 space-y-2">
          <div className="flex items-center gap-3 rounded-[20px] border border-v2-border px-3 py-2 text-sm text-v2-text-secondary">
            <Globe className="h-4 w-4 shrink-0" />
            <AnimatePresence mode="wait">
              {!collapsed && (
                <motion.div
                  key="lang-select"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="w-full"
                >
                  <LanguageSwitcher
                    variant="select"
                    className="w-full cursor-pointer bg-transparent text-sm text-v2-text-primary outline-none"
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <button
            onClick={handleLogout}
            aria-label={ts('sign_out')}
            className="flex w-full items-center gap-3 rounded-[20px] border border-transparent px-3 py-2 text-sm text-v2-text-secondary transition-colors duration-150 hover:border-v2-error hover:text-v2-error focus-visible:verge-focus"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            <AnimatePresence mode="wait">
              {!collapsed && (
                <motion.span
                  key="signout-text"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="verge-label"
                >
                  {ts('sign_out')}
                </motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>

        <button
          onClick={() => setCollapsed(prev => !prev)}
          className="absolute -right-3 top-24 flex h-6 w-6 items-center justify-center rounded-full border border-v2-border bg-v2-bg text-v2-text-secondary transition-colors duration-150 hover:border-v2-accent hover:text-v2-accent focus-visible:verge-focus"
          aria-label={collapsed ? ts('expand_aria') : ts('collapse_aria')}
        >
          <ChevronLeft
            className={`h-3.5 w-3.5 transition-transform duration-200 ${
              collapsed ? 'rotate-180' : ''
            }`}
          />
        </button>
      </motion.aside>

      <AnimatePresence>
        {searchOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            role="dialog"
            aria-modal="true"
            aria-label={ts('search_pages_aria')}
            className="fixed inset-0 z-50 bg-black/60"
            onClick={() => { setSearchOpen(false); setSearchQuery('') }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: -10 }}
              transition={{ duration: 0.15 }}
              className="absolute left-1/2 top-[15%] w-[calc(100%-32px)] max-w-lg -translate-x-1/2"
              onClick={e => e.stopPropagation()}
            >
              <div className="overflow-hidden rounded-[24px] border border-v2-accent bg-v2-bg">
                <div className="flex h-12 items-center gap-3 border-b border-v2-border px-4">
                  <Search className="h-4 w-4 text-v2-accent" />
                  <input
                    autoFocus
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder={ts('search_placeholder')}
            aria-label={ts('search_pages_aria')}
                    className="flex-1 bg-transparent text-sm text-v2-text-primary outline-none placeholder:text-v2-text-secondary/70"
                  />
                  <kbd className="rounded border border-v2-border px-1.5 py-0.5 font-mono text-[10px] text-v2-text-secondary">
                    ESC
                  </kbd>
                </div>
                {searchQuery && searchResults.length > 0 && (
                  <div className="max-h-64 space-y-1 overflow-y-auto p-2">
                    {searchResults.map(item => {
                      const Icon = item.icon
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onClick={() => { setSearchOpen(false); setSearchQuery('') }}
                          className="flex h-10 items-center gap-3 rounded-[20px] border border-transparent px-3 text-sm text-v2-text-secondary transition-colors duration-150 hover:border-v2-accent hover:text-v2-link-hover focus-visible:verge-focus"
                        >
                          <Icon className="h-4 w-4 shrink-0" />
                          <span className="verge-label">{t(item.labelKey)}</span>
                        </Link>
                      )
                    })}
                  </div>
                )}
                {searchQuery && searchResults.length === 0 && (
                  <div className="p-8 text-center text-sm text-v2-text-secondary">
                    {ts('no_results', { query: searchQuery })}
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
