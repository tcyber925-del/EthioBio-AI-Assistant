'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { useSignUp } from '@clerk/nextjs'
import { isClerkAPIResponseError } from '@clerk/nextjs/errors'
import { ErrorAlert } from '@/components/ui/errors'
import { FormField } from '@/components/ui/FormField'
import { StepDots } from '@/components/ui/StepDots'
import { clearSignupIntent } from '@/lib/auth/signupIntent'
import { tryCompleteSignup } from '@/lib/auth/completeSignup'
import {
  requestedNextFromLocation,
  resolvePostAuthDestinationOr,
  type PostAuthMe,
} from '@/lib/auth/resolveDestination'
import { fetchWithAuthJson } from '@/lib/fetchWithAuth'
import { normalizeException, type AppError } from '@/lib/errors'

export default function VerifyPage() {
  const t = useTranslations('signup')
  const tLogin = useTranslations('login')
  const router = useRouter()
  const { signUp, isLoaded, setActive } = useSignUp()
  const [code, setCode] = useState('')
  const [error, setError] = useState<AppError | null>(null)
  const [loading, setLoading] = useState(false)
  const [resent, setResent] = useState(false)

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isLoaded || !signUp) return
    setError(null)
    setLoading(true)
    try {
      const result = await signUp.attemptVerification({ strategy: 'email_code', code })
      if (result.status === 'complete' && result.createdSessionId) {
        await setActive({ session: result.createdSessionId })
        const completed = await tryCompleteSignup()
        let me: PostAuthMe | null = null
        let failure: unknown = null
        if (completed) {
          me = completed
        } else {
          try {
            me = await fetchWithAuthJson<PostAuthMe>('/auth/me')
          } catch (err) {
            failure = err
          }
        }
        clearSignupIntent()
        router.push(resolvePostAuthDestinationOr(me, failure, requestedNextFromLocation()))
      }
    } catch (err) {
      setError(
        isClerkAPIResponseError(err)
          ? {
              category: 'authentication',
              code: err.errors[0]?.code ?? 'clerk_error',
              message: err.errors[0]?.longMessage ?? err.errors[0]?.message,
              retryable: true,
            }
          : normalizeException(err),
      )
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    if (!isLoaded || !signUp) return
    setResent(false)
    try {
      await signUp.prepareVerification({ strategy: 'email_code' })
      setResent(true)
    } catch {
      setError(normalizeException(new Error('resend_failed')))
    }
  }

  return (
    <form onSubmit={handleVerify} className="space-y-5">
      <div className="text-center">
        <h1 className="text-display text-2xl text-v2-text-primary">{tLogin('verify_email_title')}</h1>
        <p className="mt-2 text-sm text-v2-text-secondary">{tLogin('check_email')}</p>
      </div>

      {error && <ErrorAlert error={error} title={tLogin('error')} />}

      <FormField label={tLogin('verify_code')} required htmlFor="signup-code">
        <input
          id="signup-code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          required
          maxLength={6}
          value={code}
          onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
          placeholder={tLogin('verify_code_placeholder')}
          className="w-full rounded-lg border border-v2-border bg-v2-surface px-3 py-2.5 text-center text-lg tracking-[0.3em] text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
        />
      </FormField>

      <button
        type="submit"
        disabled={loading || code.length !== 6}
        className="w-full rounded-lg bg-v2-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-v2-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus disabled:opacity-50"
      >
        {loading ? tLogin('please_wait') : tLogin('verify_button')}
      </button>

      <p className="text-center text-xs text-v2-text-secondary">
        <button
          type="button"
          onClick={handleResend}
          className="font-medium text-v2-accent hover:text-v2-accent-hover"
        >
          {resent ? t('code_resent') : t('resend_code')}
        </button>
      </p>

      <StepDots current={3} total={3} label={t('step_of', { current: 3, total: 3 })} />
    </form>
  )
}
