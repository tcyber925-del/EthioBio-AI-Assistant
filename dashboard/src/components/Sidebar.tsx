'use client'

import { Activity, BarChart3, BookOpen, ClipboardCheck, FileText, GraduationCap, Home, LogOut, MessageSquare, School, Shield, User, Users } from 'lucide-react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { clearToken, getUserRole, isAuthenticated } from '@/lib/auth'

const allLinks = [
  { href: '/', label: 'Dashboard', icon: Home, roles: ['admin'] },
  { href: '/classroom', label: 'Classroom', icon: School, roles: ['admin', 'teacher', 'student'] },
  { href: '/school', label: 'School', icon: Shield, roles: ['admin'] },
  { href: '/parent', label: 'Parent', icon: User, roles: ['parent', 'admin'] },
  { href: '/recovery', label: 'Recovery', icon: Activity, roles: ['admin', 'teacher'] },
  { href: '/quizzes', label: 'Quizzes', icon: ClipboardCheck, roles: ['admin', 'teacher'] },
  { href: '/lessons', label: 'Lesson Plans', icon: FileText, roles: ['admin', 'teacher'] },
  { href: '/students', label: 'Students', icon: Users, roles: ['admin', 'teacher'] },
  { href: '/monitoring', label: 'Monitoring', icon: BarChart3, roles: ['admin'] },
  { href: '/diagrams', label: 'Diagrams', icon: BarChart3, roles: ['admin', 'teacher', 'student', 'parent'] },
  { href: '/ask', label: 'Ask Q&A', icon: MessageSquare, roles: ['admin', 'teacher', 'student', 'parent'] },
]

export default function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const authenticated = isAuthenticated()
  const role = getUserRole()

  const handleLogout = () => {
    clearToken()
    router.push('/login')
  }

  if (!authenticated) return null

  const links = allLinks.filter(l => !role || l.roles.includes(role))

  return (
    <aside className="w-64 bg-card border-r border-border h-screen overflow-y-auto flex flex-col flex-shrink-0">
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="font-bold text-foreground text-sm">EthioBio</h2>
            <p className="text-xs text-foreground-muted">
              {role === 'admin' ? 'Admin Panel' : role === 'parent' ? 'Parent Dashboard' : 'Teacher Dashboard'}
            </p>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {links.map(link => {
          const Icon = link.icon
          const active = pathname === link.href || (link.href !== '/' && pathname.startsWith(link.href))
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? 'bg-primary/10 text-primary'
                  : 'text-foreground-muted hover:bg-background-secondary hover:text-foreground'
              }`}
            >
              <Icon className="w-5 h-5" />
              {link.label}
            </Link>
          )
        })}
      </nav>
      <div className="p-3 border-t border-border">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-foreground-muted hover:text-red-400 hover:bg-red-500/10 w-full transition-colors"
        >
          <LogOut className="w-5 h-5" />
          Sign Out
        </button>
      </div>
      <div className="p-4 border-t border-border text-xs text-foreground-muted">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4" />
          <span>Grade 9-12 curriculum</span>
        </div>
        <p className="mt-1 text-foreground-muted/60">gemma4:31b-cloud</p>
      </div>
    </aside>
  )
}
