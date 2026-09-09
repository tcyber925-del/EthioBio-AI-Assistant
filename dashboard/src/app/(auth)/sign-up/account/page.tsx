'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth, useSignUp } from '@clerk/nextjs'
import { isClerkAPIResponseError } from '@clerk/nextjs/errors'
import { ErrorAlert } from '@/components/ui/errors'
import { FormField } from '@/components/ui/FormField'
import OAuthButton, { type OAuthProvider } from '@/components/ui/OAuthButton'
import { StepDots } from '@/components/ui/StepDots'
import {
  clearSignupIntent,
  loadSignupIntent,
  normalizeRole,
  saveSignupIntent,
  type SignupRole,
} from '@/lib/auth/signupIntent'
import { postSignupIntent, tryCompleteSignup } from '@/lib/auth/completeSignup'
import {
  requestedNextFromLocation,
  resolvePostAuthDestination,
  type PostAuthMe,
} from '@/lib/auth/resolveDestination'
import { fetchWithAuthJson } from '@/lib/fetchWithAuth'
import { normalizeException, type AppError } from '@/lib/errors'

function AccountForm() {
  const t = useTranslations('signup')
  const tLogin = useTranslations('login')
  const router = useRouter()
  const params = useSearchParams()
  const { isSignedIn } = useAuth()
  const { signUp, isLoaded, setActive } = useSignUp()

  const role: SignupRole | null = normalizeRole(params.get('role')) ?? loadSignupIntent()?.role ?? null

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [tosAccepted, setTosAccepted] = useState(false)
  const [error, setError] = useState<AppError | null>(null)
  const [loading, setLoading] = useState<OAuthProvider | 'email' | 'resume' | null>(null)

  if (!role) {
    router.replace('/sign-up')
    return null
  }

  const clerkError = (err: unknown): AppError =>
    isClerkAPIResponseError(err)
      ? {
          category: 'authentication',
          code: err.errors[0]?.code ?? 'clerk_error',
          message: err.errors[0]?.longMessage ?? err.errors[0]?.message,
          retryable: true,
        }
      : normalizeException(err)

  /** Post the intent cookie now, finish role claim after the Clerk session exists. */
  const finalizeAfterSession = async () => {
    const completed = await tryCompleteSignup()
    const me: PostAuthMe | null =
      completed ?? (await fetchWithAuthJson<PostAuthMe>('/auth/me').catch(() => null))
    clearSignupIntent()
    router.push(resolvePostAuthDestination(me, requestedNextFromLocation()))
  }

  const submitIntent = async (): Promise<boolean> => {
    if (!tosAccepted) {
      setError({
        category: 'validation',
        code: 'tos_required',
        message: t('tos_required_error'),
        retryable: false,
      })
      return false
    }
    const draft = loadSignupIntent()
    try {
      await postSignupIntent({
        role,
        dob: draft?.dob,
        parent_email: draft?.parentEmail,
        tos_accepted: true,
      })
      saveSignupIntent({ role, dob: draft?.dob, parentEmail: draft?.parentEmail })
      return true
    } catch (err) {
      setError(normalizeException(err))
      return false
    }
  }

  const handleOAuth = async (provider: OAuthProvider) => {
    if (!isLoaded || !signUp) return
    setError(null)
    setLoading(provider)
    if (!(await submitIntent())) {
      setLoading(null)
      return
    }
    try {
      await signUp.authenticateWithRedirect({
        strategy: provider === 'google' ? 'oauth_google' : 'oauth_microsoft',
        redirectUrl: '/sso-callback',
        redirectUrlComplete: '/v2/overview',
      })
    } catch (err) {
      setError(clerkError(err))
      setLoading(null)
    }
  }

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isLoaded || !signUp) return
    setError(null)
    setLoading('email')
    if (!(await submitIntent())) {
      setLoading(null)
      return
    }
    try {
      const result = await signUp.create({ emailAddress: email, password })
      if (result.status === 'complete' && result.createdSessionId) {
        await setActive({ session: result.createdSessionId })
        await finalizeAfterSession()
        return
      }
      await signUp.prepareVerification({ strategy: 'email_code' })
      router.push('/sign-up/verify')
    } catch (err) {
      setError(clerkError(err))
    } finally {
      setLoading(null)
    }
  }

  /** OAuth user with an expired intent cookie: re-post intent + claim, no new account. */
  const handleResume = async () => {
    setError(null)
    setLoading('resume')
    if (await submitIntent()) {
      try {
        await finalizeAfterSession()
      } catch (err) {
        setError(normalizeException(err))
      }
    }
    setLoading(null)
  }

  return (
    <div className="space-y-5">
      <Link
        href="/sign-up"
        className="inline-flex items-center gap-1 text-sm font-medium text-v2-accent hover:text-v2-accent-hover"
      >
        <span aria-hidden>←</span> {t('choose_different_role')}
      </Link>

      <h1 className="text-display text-2xl text-v2-text-primary">
        {t('account_title', { role: t(`role_${role === 'student' ? 'learner' : role}`) })}
      </h1>

      {error && <ErrorAlert error={error} title={tLogin('error')} />}

      <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-v2-border bg-v2-surface p-3 text-sm text-v2-text-secondary has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-v2-focus">
        <input
          type="checkbox"
          checked={tosAccepted}
          onChange={e => setTosAccepted(e.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-v2-border accent-[#14B8A6]"
        />
        <span>
          {t.rich('tos_agree', {
            tos: chunks => (
              <Link href="/terms" className="text-v2-accent hover:text-v2-accent-hover">
                {chunks}
              </Link>
            ),
            privacy: chunks => (
              <Link href="/privacy" className="text-v2-accent hover:text-v2-accent-hover">
                {chunks}
              </Link>
            ),
          })}
        </span>
      </label>

      {isSignedIn ? (
        <button
          type="button"
          onClick={handleResume}
          disabled={loading !== null}
          className="w-full rounded-lg bg-v2-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-v2-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus disabled:opacity-50"
        >
          {loading === 'resume' ? tLogin('please_wait') : t('continue')}
        </button>
      ) : (
        <>
          <div className="space-y-2">
            <OAuthButton
              provider="google"
              label={tLogin('continue_with_google')}
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

          <form onSubmit={handleEmailSubmit} className="space-y-4">
            <FormField label={tLogin('email')} required htmlFor="signup-email">
              <input
                id="signup-email"
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder={tLogin('email_placeholder')}
                className="w-full rounded-lg border border-v2-border bg-v2-surface px-3 py-2.5 text-sm text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
              />
            </FormField>

            <FormField
              label={tLogin('password')}
              required
              htmlFor="signup-password"
              hint={t('password_hint')}
            >
              <div className="relative">
                <input
                  id="signup-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={8}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder={tLogin('password_placeholder')}
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

            <button
              type="submit"
              disabled={loading !== null || !isLoaded}
              className="w-full rounded-lg bg-v2-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-v2-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus disabled:opacity-50"
            >
              {loading === 'email' ? tLogin('please_wait') : tLogin('create_and_sign_in')}
            </button>
          </form>

          <p className="text-center text-xs text-v2-text-secondary">
            {tLogin('already_have_account')}{' '}
            <Link href="/login" className="font-medium text-v2-accent hover:text-v2-accent-hover">
              {tLogin('sign_in')}
            </Link>
          </p>
        </>
      )}

      <StepDots current={2} total={3} label={t('step_of', { current: 2, total: 3 })} />
    </div>
  )
}

export default function AccountPage() {
  return (
    <Suspense>
      <AccountForm />
    </Suspense>
  )
}
