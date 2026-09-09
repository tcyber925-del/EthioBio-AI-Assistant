'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { useSignIn } from '@clerk/nextjs'
import { isClerkAPIResponseError } from '@clerk/nextjs/errors'
import { ErrorAlert } from '@/components/ui/errors'
import { FormField } from '@/components/ui/FormField'
import { normalizeException, type AppError } from '@/lib/errors'

type Step = 'email' | 'reset'

export default function ForgotPasswordPage() {
  const t = useTranslations('forgot_password')
  const router = useRouter()
  const { signIn, isLoaded, setActive } = useSignIn()
  const [step, setStep] = useState<Step>('email')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<AppError | null>(null)
  const [loading, setLoading] = useState(false)

  const clerkError = (err: unknown): AppError =>
    isClerkAPIResponseError(err)
      ? {
          category: 'authentication',
          code: err.errors[0]?.code ?? 'clerk_error',
          message: err.errors[0]?.longMessage ?? err.errors[0]?.message,
          retryable: true,
        }
      : normalizeException(err)

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isLoaded || !signIn) return
    setError(null)
    setLoading(true)
    try {
      await signIn.create({ strategy: 'reset_password_email_code', identifier: email })
      setStep('reset')
    } catch (err) {
      setError(clerkError(err))
    } finally {
      setLoading(false)
    }
  }

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isLoaded || !signIn) return
    setError(null)
    setLoading(true)
    try {
      const attempt = await signIn.attemptFirstFactor({
        strategy: 'reset_password_email_code',
        code,
      })
      if (attempt.status !== 'needs_new_password') {
        setError({
          category: 'authentication',
          code: 'invalid_reset_code',
          message: t('invalid_code'),
          retryable: false,
        })
        return
      }
      const reset = await signIn.resetPassword({ password })
      if (reset.status === 'complete' && reset.createdSessionId) {
        await setActive({ session: reset.createdSessionId })
      }
      router.push('/login')
    } catch (err) {
      setError(clerkError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-display text-2xl text-v2-text-primary">{t('title')}</h1>
        <p className="mt-2 text-sm text-v2-text-secondary">{t('subtitle')}</p>
      </div>

      {error && <ErrorAlert error={error} title={t('title')} />}

      {step === 'email' ? (
        <form onSubmit={handleSendCode} className="space-y-4">
          <FormField label={t('email_label')} required htmlFor="reset-email">
            <input
              id="reset-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder={t('email_placeholder')}
              className="w-full rounded-lg border border-v2-border bg-v2-surface px-3 py-2.5 text-sm text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
            />
          </FormField>

          <button
            type="submit"
            disabled={loading || !isLoaded}
            className="w-full rounded-lg bg-v2-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-v2-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus disabled:opacity-50"
          >
            {t('send_code')}
          </button>

          <p className="text-center text-xs text-v2-text-secondary">
            <Link href="/login" className="font-medium text-v2-accent hover:text-v2-accent-hover">
              {t('back_to_login')}
            </Link>
          </p>
        </form>
      ) : (
        <form onSubmit={handleReset} className="space-y-4">
          <p className="text-sm text-v2-text-secondary">{t('check_email')}</p>

          <FormField label={t('code_label')} required htmlFor="reset-code">
            <input
              id="reset-code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              maxLength={6}
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
              placeholder={t('code_placeholder')}
              className="w-full rounded-lg border border-v2-border bg-v2-surface px-3 py-2.5 text-sm text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
            />
          </FormField>

          <FormField label={t('new_password_label')} required htmlFor="reset-password">
            <input
              id="reset-password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={t('new_password_placeholder')}
              className="w-full rounded-lg border border-v2-border bg-v2-surface px-3 py-2.5 text-sm text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
            />
          </FormField>

          <button
            type="submit"
            disabled={loading || !isLoaded || code.length !== 6 || password.length < 8}
            className="w-full rounded-lg bg-v2-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-v2-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus disabled:opacity-50"
          >
            {t('set_password')}
          </button>
        </form>
      )}
    </div>
  )
}