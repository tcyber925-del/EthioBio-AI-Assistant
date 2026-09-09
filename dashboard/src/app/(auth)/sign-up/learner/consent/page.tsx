'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { FormField } from '@/components/ui/FormField'
import { StepDots } from '@/components/ui/StepDots'
import { loadSignupIntent, saveSignupIntent } from '@/lib/auth/signupIntent'

export default function LearnerConsentPage() {
  const t = useTranslations('signup')
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [errorKey, setErrorKey] = useState<string | null>(null)

  useEffect(() => {
    const intent = loadSignupIntent()
    if (!intent?.dob || intent.role !== 'student') {
      router.replace('/sign-up/learner')
    }
  }, [router])

  const handleContinue = () => {
    setErrorKey(null)
    const trimmed = email.trim()
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(trimmed)) {
      setErrorKey('signup.parent_email_invalid')
      return
    }
    const intent = loadSignupIntent()
    saveSignupIntent({ role: 'student', dob: intent?.dob, parentEmail: trimmed })
    router.push('/sign-up/account?role=student')
  }

  return (
    <div className="space-y-6">
      <Link
        href="/sign-up/learner"
        className="inline-flex items-center gap-1 text-sm font-medium text-v2-accent hover:text-v2-accent-hover"
      >
        <span aria-hidden>←</span> {t('back')}
      </Link>

      <div>
        <h1 className="text-display text-2xl text-v2-text-primary">{t('consent_title')}</h1>
        <p className="mt-2 text-sm text-v2-text-secondary">{t('consent_body')}</p>
      </div>

      <FormField
        label={t('parent_email_label')}
        required
        errorField="parent_email"
        errorMessages={errorKey ? [errorKey] : []}
        hint={t('parent_email_hint')}
      >
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder={t('parent_email_placeholder')}
          className="w-full rounded-lg border border-v2-border bg-v2-surface px-3 py-2.5 text-sm text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
        />
      </FormField>

      <button
        type="button"
        onClick={handleContinue}
        className="w-full rounded-lg bg-v2-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-v2-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
      >
        {t('continue')}
      </button>

      <StepDots current={1} total={3} label={t('step_of', { current: 1, total: 3 })} />
    </div>
  )
}
