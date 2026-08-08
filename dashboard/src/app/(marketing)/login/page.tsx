'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { GraduationCap, AlertTriangle, Eye, EyeOff } from 'lucide-react'
import { setToken } from '@/lib/auth'
import { setCookie } from '@/lib/cookies'
import { fetchWithTimeout } from '@/lib/fetch'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isRegister, setIsRegister] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [loginMode, setLoginMode] = useState<'email' | 'telegram'>('email')
  const [telegramId, setTelegramId] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [selectedRole, setSelectedRole] = useState('teacher')
  const t = useTranslations('login')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      if (isRegister) {
        await fetchWithTimeout('/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, role: selectedRole }),
        })
      }

      const data = await fetchWithTimeout('/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      setToken(data.access_token)
      if (data.language_preference) {
        setCookie('NEXT_LOCALE', data.language_preference, 365)
      }
      router.push('/classroom')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const sendOtp = async () => {
    if (!telegramId.trim()) return
    setLoading(true)
    setError(null)
    try {
      await fetchWithTimeout('/auth/request-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telegram_id: Number(telegramId) }),
      })
      setOtpSent(true)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const verifyOtp = async () => {
    if (!otpCode.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithTimeout('/auth/verify-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telegram_id: Number(telegramId), otp: otpCode }),
      })
      setToken(data.access_token)
      router.push('/v2/overview')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

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

        {loginMode === 'email' ? (
          <form onSubmit={handleSubmit} className="bg-card rounded-xl border border-border p-6 space-y-4">
            <h2 className="text-lg font-semibold text-foreground text-center">
              {isRegister ? t('create_account') : t('sign_in')}
            </h2>

            {error && (
              <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

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

            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-foreground-muted mb-2">{t('register_as')}</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: 'teacher', label: t('teacher') },
                    { value: 'student', label: t('student') },
                    { value: 'parent', label: t('parent') },
                  ].map(r => (
                    <button
                      key={r.value}
                      type="button"
                      onClick={() => setSelectedRole(r.value)}
                      className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                        selectedRole === r.value
                          ? 'bg-primary/10 border-primary text-primary'
                          : 'bg-background border-border text-foreground-muted hover:border-foreground-muted'
                      }`}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-white rounded-lg py-2.5 text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50"
            >
              {loading ? t('please_wait') : isRegister ? t('create_and_sign_in') : t('sign_in')}
            </button>

            <p className="text-xs text-center text-foreground-muted">
              {isRegister ? (
                <>{t('already_have_account')}{' '}<button type="button" onClick={() => setIsRegister(false)} className="text-primary hover:underline">{t('sign_in')}</button></>
              ) : (
                <>{t('new_teacher')}{' '}<button type="button" onClick={() => setIsRegister(true)} className="text-primary hover:underline">{t('create_account')}</button></>
              )}
            </p>

            <div className="border-t border-border pt-4 mt-4 space-y-2">
              <a
                href="/auth/oauth/google/login?redirect=/classroom"
                className="w-full flex items-center justify-center gap-2 py-2 bg-card border border-border text-foreground rounded-lg text-sm hover:bg-border transition-colors"
              >
                <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden="true">
                  <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                  <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                  <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                  <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
                </svg>
                {t('continue_with_google')}
              </a>
              <button type="button" onClick={() => setLoginMode('telegram')}
                className="w-full py-2 bg-card border border-border text-foreground rounded-lg text-sm hover:bg-border transition-colors">
                {t('login_telegram')}
              </button>
            </div>
          </form>
        ) : (
          <div className="bg-card rounded-xl border border-border p-6">
            <h2 className="text-lg font-semibold text-foreground text-center mb-4">{t('telegram_otp')}</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground-muted mb-1">{t('telegram_id')}</label>
                <input
                  type="number" value={telegramId} onChange={e => setTelegramId(e.target.value)}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
                  placeholder={t('telegram_id_hint')} disabled={otpSent}
                />
              </div>
              {!otpSent ? (
                <button onClick={sendOtp} disabled={loading || !telegramId.trim()}
                  className="w-full bg-primary text-white rounded-lg py-2.5 text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50">
                  {loading ? t('sending') : t('send_otp')}
                </button>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-foreground-muted mb-1">{t('otp_code')}</label>
                    <input
                      type="text" value={otpCode} onChange={e => setOtpCode(e.target.value)}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2.5 text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
                      placeholder={t('otp_placeholder')} maxLength={6}
                    />
                  </div>
                  <button onClick={verifyOtp} disabled={loading || otpCode.length !== 6}
                    className="w-full bg-primary text-white rounded-lg py-2.5 text-sm font-medium hover:bg-primary-hover transition-colors disabled:opacity-50">
                    {loading ? t('verifying') : t('verify_login')}
                  </button>
                </>
              )}
              {error && <p className="text-sm text-red-400">{error}</p>}
              <div className="border-t border-border pt-4 mt-4">
                <button type="button" onClick={() => { setLoginMode('email'); setOtpSent(false); setOtpCode(''); setTelegramId(''); setError(null) }}
                  className="w-full py-2 bg-card border border-border text-foreground rounded-lg text-sm hover:bg-border transition-colors">
                  {t('back_to_email')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
