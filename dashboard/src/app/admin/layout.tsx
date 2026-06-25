'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getToken } from '@/lib/auth'

const NAV_ITEMS = [
  { href: '/admin', label: 'Dashboard', icon: '📊' },
  { href: '/admin/review', label: 'Review Queue', icon: '🚩' },
  { href: '/admin/content', label: 'Content Review', icon: '📝' },
  { href: '/admin/schools', label: 'Schools', icon: '🏫' },
  { href: '/admin/users', label: 'Users', icon: '👥' },
  { href: '/admin/monitoring', label: 'Monitoring', icon: '📡' },
  { href: '/admin/agents', label: 'Agents', icon: '🤖' },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [authorized, setAuthorized] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    const token = getToken()
    if (!token) {
      router.push('/login')
      return
    }
    fetchWithAuth('/admin/dashboard')
      .then(() => setAuthorized(true))
      .catch(err => {
        const msg = err instanceof Error ? err.message : String(err)
        if (msg.includes('401') || msg.includes('Session expired')) {
          router.push('/login')
        } else if (msg.includes('403')) {
          setError('Access denied — admin privileges required')
        } else {
          setError(msg)
        }
      })
  }, [router])

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <h2 className="text-xl font-bold text-red-400 mb-2">Access Denied</h2>
          <p className="text-foreground-muted mb-4">{error}</p>
          <Link href="/" className="text-primary hover:underline text-subhead">
            Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (authorized === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-foreground-muted text-body">Verifying access...</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="w-56 bg-card border-r border-border flex flex-col">
        <div className="p-4 border-b border-border">
          <h1 className="font-display font-bold text-lg text-foreground">Admin Panel</h1>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {NAV_ITEMS.map(item => (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg text-subhead transition-colors ${
                pathname === item.href
                  ? 'bg-primary/10 text-primary'
                  : 'text-foreground-muted hover:bg-background-secondary hover:text-foreground'
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t border-border">
          <Link href="/" className="flex items-center gap-2 text-small text-foreground-muted hover:text-foreground transition-colors">
            <span>←</span>
            <span>Back to Dashboard</span>
          </Link>
        </div>
      </aside>
      <main className="flex-1 p-6">
        {children}
      </main>
    </div>
  )
}
