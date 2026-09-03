'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { GraduationCap, Eye, EyeOff } from 'lucide-react'
import { useSignIn, useSignUp } from '@clerk/nextjs'
import { isClerkAPIResponseError } from '@clerk/nextjs/errors'
import { ErrorAlert } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'
import { safeNextPath } from '@/lib/safeNextPath'

export default function LoginPage() {
  const router = useRouter()
  const { signIn, isLoaded: signInLoaded, setActive: setActiveSignIn } = useSignIn()
  const { signUp, isLoaded: signUpLoaded, setActive: setActiveSignUp } = useSignUp()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [isRegister, setIsRegister] = useState(false)
  const [verifyStep, setVerifyStep] = useState(false)
  const [error, setError] = useState<AppError | null>(null)
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const t = useTranslations('login')

  const finish = () => {
    const params = new URLSearchParams(window.location.search)
    const target = params.get('next') ?? params.get('redirect_url')
    router.push(target ? safeNextPath(`?next=${encodeURIComponent(target)}`, window.location.origin) ?? '/v2/overview' : '/v2/overview')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (isRegister) {
        const result = await signUp?.create({ emailAddress: email, password })
        if (result?.status === 'complete' && result.createdSessionId) {
          await setActiveSignUp?.({ session: result.createdSessionId })
          finish()
          return
        }
        await signUp?.prepareVerification({ strategy: 'email_code' })
        setVerifyStep(true)
        return
      }

      const result = await signIn?.create({ identifier: email, password })
      if (result?.status === 'complete' && result.createdSessionId) {
        await setActiveSignIn?.({ session: result.createdSessionId })
        finish()
      }
    } catch (err) {
      if (isClerkAPIResponseError(err)) {
        const message = err.errors[0]?.longMessage ?? err.errors[0]?.message ?? t('error')
        setError({ category: 'authentication', code: err.errors[0]?.code ?? 'clerk_error', message, retryable: true })
      } else {
        setError(normalizeException(err))
      }
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const result = await signUp?.attemptVerification({ strategy: 'email_code', code })
      if (result?.status === 'complete' && result.createdSessionId) {
        await setActiveSignUp?.({ session: result.createdSessionId })
        finish()
      }
    } catch (err) {
      if (isClerkAPIResponseError(err)) {
        const message = err.errors[0]?.longMessage ?? err.errors[0]?.message ?? t('error')
        setError({ category: 'authentication', code: err.errors[0]?.code ?? 'clerk_error', message, retryable: true })
      } else {
        setError(normalizeException(err))
      }
    } finally {
      setLoading(false)
    }
  }

  const handleGoogle = () => {
    const method = isRegister ? signUp : signIn
    method?.authenticateWithRedirect({
      strategy: 'oauth_google',
      redirectUrl: '/sso-callback',
      redirectUrlComplete: '/v2/overview',
    })
  }

  const loaded = isRegister ? signUpLoaded : signInLoaded

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-3 justify-center mb-8">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <GraduationCap className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-foreground">{t('brand_short')}</h1>
            <p className="text-xs text-foreground-muted">{t('teacher_dashboard')}</p>
          </div>
        </div>

        {verifyStep ? (
          <form onSubmit={handleVerifyCode} className="bg-card rounded-xl border border-border p-6 space-y-4">
            <h2 className="text-lg font-semibold text-foreground text-center">{t('verify_email_title')}</h2>
            <p className="text-xs text-foreground-muted text-center">{t('check_email')}</p>
            {error && <ErrorAlert error={error} title={t('error')} />}
            <div>
              <label className="block text-sm font-medium text-foreground-muted mb-1">{t('verify_code')}</label>
              <input
                type="text"
                required
                maxLength={6}
                value={code}
                onChange={e => setCode(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
                placeholder={t('verify_code_placeholder')}
              />
            </div>
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="w-full bg-primary text-white rounded-lg py-2.5 text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
            >
              {loading ? t('please_wait') : t('verify_button')}
            </button>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="bg-card rounded-xl border border-border p-6 space-y-4">
            <h2 className="text-lg font-semibold text-foreground text-center">
              {isRegister ? t('create_account') : t('sign_in')}
            </h2>

            {error && <ErrorAlert error={error} title={t('error')} />}

            <div>
              <label className="block text-sm font-medium text-foreground-muted mb-1">{t('email')}</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
                placeholder={t('email_placeholder')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground-muted mb-1">{t('password')}</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={6}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2.5 pr-10 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
                  placeholder={t('password_placeholder')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-muted hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !loaded}
              className="w-full bg-primary text-white rounded-lg py-2.5 text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
            >
              {loading ? t('please_wait') : isRegister ? t('create_and_sign_in') : t('sign_in')}
            </button>

            <p className="text-xs text-center text-foreground-muted">
              {isRegister ? (
                <>{t('already_have_account')}{' '}<button type="button" onClick={() => { setIsRegister(false); setError(null) }} className="text-primary hover:underline">{t('sign_in')}</button></>
              ) : (
                <>{t('new_teacher')}{' '}<button type="button" onClick={() => { setIsRegister(true); setError(null) }} className="text-primary hover:underline">{t('create_account')}</button></>
              )}
            </p>

            <div className="border-t border-border pt-4 mt-4">
              <button
                type="button"
                onClick={handleGoogle}
                disabled={!loaded}
                className="w-full flex items-center justify-center gap-2 py-2 bg-card border border-border text-foreground rounded-lg text-sm hover:bg-border transition-colors disabled:opacity-50"
              >
                <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
                </svg>
                {t('continue_with_google')}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}