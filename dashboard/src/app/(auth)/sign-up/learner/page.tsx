'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { FormField } from '@/components/ui/FormField'
import Select from '@/components/ui/Select'
import { StepDots } from '@/components/ui/StepDots'
import { ageFromDob, loadSignupIntent, saveSignupIntent } from '@/lib/auth/signupIntent'

// Mirrors settings.min_self_consent_age on the backend; server re-validates.
const MIN_SELF_CONSENT_AGE = 13

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)
const DAYS = Array.from({ length: 31 }, (_, i) => i + 1)

type DobErrorKey = 'signup.dob_required' | 'signup.dob_invalid' | null

export default function LearnerDobPage() {
  const t = useTranslations('signup')
  const locale = useLocale()
  const router = useRouter()
  const [month, setMonth] = useState('')
  const [day, setDay] = useState('')
  const [year, setYear] = useState('')
  const [errorKey, setErrorKey] = useState<DobErrorKey>(null)

  const years = useMemo(() => {
    const current = new Date().getFullYear()
    return Array.from({ length: 96 }, (_, i) => current - 5 - i)
  }, [])

  const monthNames = useMemo(() => {
    const fmt = new Intl.DateTimeFormat(locale, { month: 'long' })
    return new Map(MONTHS.map(m => [m, fmt.format(new Date(2000, m - 1, 1))]))
  }, [locale])

  const handleNext = () => {
    setErrorKey(null)
    const m = Number(month)
    const d = Number(day)
    const y = Number(year)
    if (!m || !d || !y) {
      setErrorKey('signup.dob_required')
      return
    }
    const parsed = new Date(y, m - 1, d)
    if (
      parsed.getFullYear() !== y ||
      parsed.getMonth() !== m - 1 ||
      parsed.getDate() !== d ||
      parsed.getTime() > Date.now()
    ) {
      setErrorKey('signup.dob_invalid')
      return
    }
    const dob = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`

    const existing = loadSignupIntent()
    saveSignupIntent({ role: 'student', dob, parentEmail: existing?.parentEmail })

    if (ageFromDob(dob) < MIN_SELF_CONSENT_AGE) {
      router.push('/sign-up/learner/consent')
    } else {
      router.push('/sign-up/account?role=student')
    }
  }

  return (
    <div className="space-y-6">
      <Link
        href="/sign-up"
        className="inline-flex items-center gap-1 text-sm font-medium text-v2-accent hover:text-v2-accent-hover"
      >
        <span aria-hidden>←</span> {t('choose_different_role')}
      </Link>

      <div>
        <h1 className="text-display text-2xl text-v2-text-primary">{t('learner_dob_title')}</h1>
        <p className="mt-2 text-sm text-v2-text-secondary">{t('learner_dob_subtitle')}</p>
      </div>

      <FormField
        label={t('dob_label')}
        required
        errorField="dob"
        errorMessages={errorKey ? [errorKey] : []}
      >
        <div className="grid grid-cols-3 gap-2">
          <Select value={month} onChange={e => setMonth(e.target.value)} aria-label={t('month')}>
            <option value="">{t('month')}</option>
            {MONTHS.map(m => (
              <option key={m} value={m}>
                {monthNames.get(m)}
              </option>
            ))}
          </Select>
          <Select value={day} onChange={e => setDay(e.target.value)} aria-label={t('day')}>
            <option value="">{t('day')}</option>
            {DAYS.map(d => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </Select>
          <Select value={year} onChange={e => setYear(e.target.value)} aria-label={t('year')}>
            <option value="">{t('year')}</option>
            {years.map(y => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </Select>
        </div>
      </FormField>

      <button
        type="button"
        onClick={handleNext}
        className="w-full rounded-lg bg-v2-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-v2-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus"
      >
        {t('next')}
      </button>

      <StepDots current={1} total={3} label={t('step_of', { current: 1, total: 3 })} />
    </div>
  )
}
