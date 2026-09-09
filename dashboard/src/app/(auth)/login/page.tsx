'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth, useSignIn } from '@clerk/nextjs'
import { isClerkAPIResponseError } from '@clerk/nextjs/errors'
import { ErrorAlert } from '@/components/ui/errors'
import { FormField } from '@/components/ui/FormField'
import OAuthButton, { type OAuthProvider } from '@/components/ui/OAuthButton'
import { tryCompleteSignup } from '@/lib/auth/completeSignup'
import {
  requestedNextFromLocation,
  resolvePostAuthDestinationOr,
  type PostAuthMe,
} from '@/lib/auth/resolveDestination'
import { fetchWithAuthJson } from '@/lib/fetchWithAuth'
import { normalizeException, type AppError } from '@/lib/errors'

export default function LoginPage() {
  const t = useTranslations('login')
  const router = useRouter()
  const { isSignedIn } = useAuth()
  const { signIn, isLoaded, setActive } = useSignIn()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<AppError | null>(null)
  const [loading, setLoading] = useState<OAuthProvider | 'email' | null>(null)

  const resolve = useCallback(async () => {
    const requestedNext = requestedNextFromLocation()
    let me: PostAuthMe | null = null
    let failure: unknown = null
    try {
      const completed = await tryCompleteSignup()
      if (completed) {
        me = completed
      } else {
        try {
          me = await fetchWithAuthJson<PostAuthMe>('/auth/me')
        } catch (err) {
          failure = err
        }
      }
    } catch (err) {
      failure = err
    }
    router.push(resolvePostAuthDestinationOr(me, failure, requestedNext))
  }, [router])

  useEffect(() => {
    if (isSignedIn) resolve()
  }, [isSignedIn, resolve])

  const clerkError = (err: unknown): AppError =>
    isClerkAPIResponseError(err)
      ? {
          category: 'authentication',
          code: err.errors[0]?.code ?? 'clerk_error',
          message: err.errors[0]?.longMessage ?? err.errors[0]?.message,
          retryable: true,
        }
      : normalizeException(err)

  const handleOAuth = async (provider: OAuthProvider) => {
    if (!isLoaded || !signIn) return
    setError(null)
    setLoading(provider)
    try {
      await signIn.authenticateWithRedirect({
        strategy: provider === 'google' ? 'oauth_google' : 'oauth_microsoft',
        redirectUrl: '/sso-callback',
        redirectUrlComplete: '/v2/overview',
      })
    } catch (err) {
      setError(clerkError(err))
      setLoading(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isLoaded || !signIn) return
    setError(null)
    setLoading('email')
    try {
      const result = await signIn.create({ identifier: email, password })
      if (result.status === 'complete') {
        if (result.createdSessionId) {
          await setActive({ session: result.createdSessionId })
        }
        await resolve()
      } else {
        setError({
          category: 'authentication',
          code: 'clerk_needs_verification',
          message: t('error'),
          retryable: false,
        })
      }
    } catch (err) {
      setError(clerkError(err))
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-display text-2xl text-v2-text-primary">{t('sign_in')}</h1>
        <p className="mt-2 text-sm text-v2-text-secondary">{t('sign_in_subtitle')}</p>
      </div>

      {error && <ErrorAlert error={error} title={t('error')} />}

      <div className="space-y-2">
        <OAuthButton
          provider="google"
          label={t('continue_with_google')}
          loading={loading === 'google'}
          disabled={loading !== null}
          onClick={() => handleOAuth('google')}
        />
        <OAuthButton
          provider="microsoft"
          label={t('continue_with_microsoft')}
          loading={loading === 'microsoft'}
          disabled={loading !== null}
          onClick={() => handleOAuth('microsoft')}
        />
      </div>

      <div className="flex items-center gap-3 text-xs text-v2-text-secondary">
        <span className="h-px flex-1 bg-v2-border" aria-hidden />
        {t('or_email')}
        <span className="h-px flex-1 bg-v2-border" aria-hidden />
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <FormField label={t('email')} required htmlFor="login-email">
          <input
            id="login-email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder={t('email_placeholder')}
            className="w-full rounded-lg border border-v2-border bg-v2-surface px-3 py-2.5 text-sm text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
          />
        </FormField>

        <FormField label={t('password')} required htmlFor="login-password">
          <div className="relative">
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              required
              autoComplete="current-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={t('password_placeholder')}
              className="w-full rounded-lg border border-v2-border bg-v2-surface px-3 py-2.5 pr-10 text-sm text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
            />
            <button
              type="button"
              onClick={() => setShowPassword(v => !v)}
              aria-label={showPassword ? t('hide_password') : t('show_password')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-v2-text-secondary hover:text-v2-text-primary"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </FormField>

        <div className="flex items-center justify-between text-xs">
          <Link
            href="/forgot-password"
            className="font-medium text-v2-accent hover:text-v2-accent-hover"
          >
            {t('forgot_password')}
          </Link>
        </div>

        <button
          type="submit"
          disabled={loading !== null || !isLoaded}
          className="w-full rounded-lg bg-v2-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-v2-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus disabled:opacity-50"
        >
          {loading === 'email' ? t('please_wait') : t('sign_in')}
        </button>
      </form>

      <p className="text-center text-xs text-v2-text-secondary">
        {t('new_here')}{' '}
        <Link href="/sign-up" className="font-medium text-v2-accent hover:text-v2-accent-hover">
          {t('create_account')}
        </Link>
      </p>
    </div>
  )
}