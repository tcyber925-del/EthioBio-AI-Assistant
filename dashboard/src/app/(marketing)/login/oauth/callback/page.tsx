'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { AlertTriangle, GraduationCap, Loader2 } from 'lucide-react'
import { setToken } from '@/lib/auth'

export default function OAuthCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const t = useTranslations('login')
  const [error, setError] = useState<string | null>(null)
  const claimed = useRef(false)

  useEffect(() => {
    const ticket = searchParams.get('ticket')
    const oauthError = searchParams.get('oauth_error')

    if (oauthError) {
      setError(oauthError)
      return
    }
    if (!ticket || claimed.current) return
    claimed.current = true

    ;(async () => {
      try {
        const res = await fetch('/auth/oauth/claim', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ticket }),
          credentials: 'include',
        })
        if (!res.ok) {
          setError('session_failed')
          return
        }
        const data = await res.json()
        setToken(data.access_token)
        let target = '/classroom'
        if (data.redirect) {
          try {
            const url = new URL(data.redirect, window.location.origin)
            if (url.origin === window.location.origin && !url.pathname.startsWith('/login')) {
              target = url.pathname + url.search + url.hash
            }
          } catch {
            // invalid redirect — fall back to default
          }
        }
        router.replace(target)
      } catch {
        setError('session_failed')
      }
    })()
  }, [router, searchParams])

  const errorMessage =
    error === 'not_configured'
      ? t('oauth_error_not_configured')
      : error === 'email_conflict' || error === 'conflict'
        ? t('oauth_error_email_conflict')
        : error === 'access_denied'
          ? t('oauth_error_access_denied')
          : error === 'session_failed'
            ? t('error')
            : error
              ? t('oauth_error_unknown')
              : null

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-card rounded-xl border border-border p-6 text-center space-y-4">
        <div className="flex items-center gap-3 justify-center">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <GraduationCap className="w-6 h-6 text-primary" />
          </div>
          <h1 className="text-xl font-bold text-foreground">{t('brand_short')}</h1>
        </div>

        {error ? (
          <>
            <div className="flex items-center justify-center gap-2 text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <a
              href="/login"
              className="inline-block px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover transition-colors"
            >
              {t('back_to_login')}
            </a>
          </>
        ) : (
          <p className="text-sm text-foreground-muted flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            {t('oauth_redirecting')}
          </p>
        )}
      </div>
    </div>
  )
}
