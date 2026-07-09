'use client'

import { Activity, BarChart3, BookOpen, ClipboardCheck, FileText, GraduationCap, Home, LayoutDashboard, LogOut, MessageSquare, School, Search, Shield, Upload, User, Users, Globe } from 'lucide-react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import { clearToken, getUserRole, getUserId, isAuthenticated } from '@/lib/auth'
import { setCookie } from '@/lib/cookies'

function CellAnimation() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" className="shrink-0" aria-hidden="true">
      <circle cx="18" cy="18" r="15" stroke="#34d399" strokeWidth="1.5" strokeDasharray="4 3" className="cell-membrane" fill="none" />
      <circle cx="18" cy="18" r="6" fill="#34d399" opacity="0.25" className="cell-nucleus" />
      <circle cx="18" cy="18" r="3" fill="#34d399" opacity="0.5" className="cell-nucleus" />
    </svg>
  )
}

export default function Sidebar() {
  const t = useTranslations('sidebar')
  const locale = useLocale()
  const pathname = usePathname()
  const router = useRouter()
  const authenticated = isAuthenticated()
  const role = getUserRole()
  const userId = getUserId()

  const allLinks = [
    { href: '/', icon: Home, roles: ['admin'] },
    { href: '/student', icon: Home, roles: ['student'] },
    { href: '/classroom', icon: School, roles: ['admin', 'teacher', 'student'] },
    { href: '/school', icon: Shield, roles: ['admin'] },
    { href: '/parent', icon: User, roles: ['parent', 'admin'] },
    { href: '/recovery', icon: Activity, roles: ['admin', 'teacher'] },
    { href: '/quizzes', icon: ClipboardCheck, roles: ['admin', 'teacher'] },
    { href: '/lessons', icon: FileText, roles: ['admin', 'teacher'] },
    { href: '/unit-plans', icon: BookOpen, roles: ['admin', 'teacher'] },
    { href: '/students', icon: Users, roles: ['admin', 'teacher'] },
    { href: '/monitoring', icon: BarChart3, roles: ['admin'] },
    { href: '/diagrams', icon: BarChart3, roles: ['admin', 'teacher', 'student', 'parent'] },
    { href: '/ask', icon: MessageSquare, roles: ['admin', 'teacher', 'student', 'parent'] },
    { href: '/workspace', icon: LayoutDashboard, roles: ['admin', 'teacher'] },
    { href: '/workspace/browse', icon: BookOpen, roles: ['admin', 'teacher'] },
    { href: '/workspace/upload', icon: Upload, roles: ['admin', 'teacher'] },
    { href: '/workspace/search', icon: Search, roles: ['admin', 'teacher'] },
    { href: '/workspace/processing', icon: Activity, roles: ['admin', 'teacher'] },
  ]

  const linkLabel = (href: string) => {
    const map: Record<string, string> = {
      '/': t('dashboard'),
      '/student': t('student_dashboard'),
      '/classroom': t('classroom'),
      '/school': t('school'),
      '/parent': t('parent'),
      '/recovery': t('recovery'),
      '/quizzes': t('quizzes'),
      '/lessons': t('lessons'),
      '/unit-plans': t('unit_plans'),
      '/students': t('students'),
      '/monitoring': t('monitoring'),
      '/diagrams': t('diagrams'),
      '/ask': t('ask'),
      '/workspace': t('workspace'),
      '/workspace/browse': t('workspace_browse'),
      '/workspace/upload': t('workspace_upload'),
      '/workspace/search': t('workspace_search'),
      '/workspace/processing': t('workspace_processing'),
    }
    return map[href] || ''
  }

  const subtitleLabel = () => {
    if (role === 'admin') return t('admin_panel')
    if (role === 'parent') return t('parent_dashboard')
    if (role === 'student') return t('student_dashboard')
    return t('teacher_dashboard')
  }

  const handleLogout = () => {
    clearToken()
    router.push('/login')
  }

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLocale = e.target.value
    setCookie('NEXT_LOCALE', newLocale, 365)
    if (userId) {
      fetch(`/api/users/${userId}/language?language=${newLocale}`, { method: 'PATCH' }).catch(() => {})
    }
    router.refresh()
  }

  if (!authenticated) return null

  const isV2Route = pathname.startsWith('/v2/') || pathname === '/v2'
  if (isV2Route) return null

  const links = allLinks.filter(l => !role || l.roles.includes(role))

  return (
    <aside className="w-64 bg-card border-r border-border h-screen overflow-y-auto flex flex-col flex-shrink-0">
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-3">
          <CellAnimation />
          <div>
            <h2 className="text-heading text-foreground">EthioBio</h2>
            <p className="text-small text-foreground-muted">{subtitleLabel()}</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {links.map(link => {
          const Icon = link.icon
          const active = pathname === link.href || (link.href !== '/' && link.href !== '/workspace' && pathname.startsWith(link.href))
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-subhead transition-all duration-150 ${
                active
                  ? 'bg-primary/10 text-primary shadow-[inset_3px_0_0_var(--primary)]'
                  : 'text-foreground-muted hover:bg-background-secondary hover:text-foreground'
              }`}
            >
              <Icon className="w-5 h-5 shrink-0" />
              {linkLabel(link.href)}
            </Link>
          )
        })}
      </nav>
      <div className="p-3 border-t border-border space-y-1">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-small text-foreground-muted">
          <Globe className="w-5 h-5 shrink-0" />
          <select
            value={locale}
            onChange={handleLanguageChange}
            className="bg-transparent text-foreground text-small outline-none cursor-pointer w-full"
          >
            <option value="en">{t('english')}</option>
            <option value="am">{t('amharic')}</option>
          </select>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-subhead text-foreground-muted hover:text-red-400 hover:bg-red-500/10 w-full transition-all duration-150"
        >
          <LogOut className="w-5 h-5 shrink-0" />
          {t('sign_out')}
        </button>
      </div>
      <div className="p-4 border-t border-border text-small text-foreground-muted">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4" />
          <span>{t('grade_curriculum')}</span>
        </div>
        <p className="mt-1 text-foreground-muted/60">gemma4:31b-cloud</p>
      </div>
    </aside>
  )
}
