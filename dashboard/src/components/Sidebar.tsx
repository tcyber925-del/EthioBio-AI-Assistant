'use client'

import { BarChart3, BookOpen, ClipboardCheck, FileText, GraduationCap, Home, MessageSquare, Users } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const links = [
  { href: '/', label: 'Dashboard', icon: Home },
  { href: '/quizzes', label: 'Quizzes', icon: ClipboardCheck },
  { href: '/lessons', label: 'Lesson Plans', icon: FileText },
  { href: '/students', label: 'Students', icon: Users },
  { href: '/monitoring', label: 'Monitoring', icon: BarChart3 },
  { href: '/ask', label: 'Ask Q&A', icon: MessageSquare },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 bg-card border-r border-border min-h-screen flex flex-col flex-shrink-0">
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="font-bold text-foreground text-sm">EthioBio</h2>
            <p className="text-xs text-foreground-muted">Teacher Dashboard</p>
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
