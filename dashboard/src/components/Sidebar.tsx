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
    <aside className="w-64 bg-white border-r min-h-screen flex flex-col">
      <div className="p-5 border-b">
        <div className="flex items-center gap-3">
          <GraduationCap className="w-7 h-7 text-green-600" />
          <div>
            <h2 className="font-bold text-gray-900 text-sm">EthioBio</h2>
            <p className="text-xs text-gray-500">Teacher Dashboard</p>
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
                  ? 'bg-green-50 text-green-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <Icon className="w-5 h-5" />
              {link.label}
            </Link>
          )
        })}
      </nav>
      <div className="p-4 border-t text-xs text-gray-400">
        <BookOpen className="w-4 h-4 inline mr-1" />
        <span>Grade 12 curriculum</span>
        <p className="mt-1">gemma4:31b-cloud</p>
      </div>
    </aside>
  )
}
