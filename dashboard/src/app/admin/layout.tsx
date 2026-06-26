'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getToken } from '@/lib/auth'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [authorized, setAuthorized] = useState<boolean | null>(null)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    const token = getToken()
    if (!token) {
      router.push('/login')
      return
    }
    fetchWithAuth('/api/admin/dashboard')
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

  return <>{children}</>
}
