'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getToken } from '@/lib/auth'
import { ErrorState } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations('admin.access')
  const [authorized, setAuthorized] = useState<boolean | null>(null)
  const [error, setError] = useState<AppError | null>(null)
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
        const error = normalizeException(err)
        if (error.category === 'authentication') {
          router.push('/login')
          return
        }
        setError(error)
      })
  }, [router])

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <ErrorState error={error} title={t('denied_title')} />
          <Link href="/" className="text-primary hover:underline text-subhead">
            {t('back_to_dashboard')}
          </Link>
        </div>
      </div>
    )
  }

  if (authorized === null) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-foreground-muted text-body">{t('verifying')}</p>
      </div>
    )
  }

  return <>{children}</>
}
