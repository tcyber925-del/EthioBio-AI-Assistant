'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { ErrorAlert } from '@/components/ui/errors'
import { FormField } from '@/components/ui/FormField'
import Select from '@/components/ui/Select'
import { fetchWithAuthJson } from '@/lib/fetchWithAuth'
import { normalizeException, type AppError } from '@/lib/errors'

const SUBJECTS = ['biology', 'chemistry', 'physics', 'mathematics'] as const
const GRADES = [7, 8, 9, 10, 11, 12] as const

interface MeShape {
  role: string
  onboarding_completed: boolean
}

export default function OnboardingPage() {
  const t = useTranslations('onboarding')
  const router = useRouter()
  const [me, setMe] = useState<MeShape | null>(null)
  const [grade, setGrade] = useState('')
  const [subject, setSubject] = useState('')
  const [error, setError] = useState<AppError | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchWithAuthJson<MeShape>('/auth/me')
      .then(data => {
        if (data.onboarding_completed) {
          router.replace('/v2/overview')
          return
        }
        setMe(data)
      })
      .catch(() => router.replace('/login'))
  }, [router])

  const handleSubmit = async () => {
    setError(null)
    setLoading(true)
    try {
      await fetchWithAuthJson('/auth/onboarding', {
        method: 'POST',
        body: JSON.stringify({
          grade_level: grade ? Number(grade) : null,
          subject: subject || null,
        }),
      })
      router.push('/v2/overview')
    } catch (err) {
      setError(normalizeException(err))
    } finally {
      setLoading(false)
    }
  }

  if (!me) {
    return <p className="py-8 text-center text-sm text-v2-text-secondary">{t('loading')}</p>
  }

  const isStudent = me.role === 'student'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-display text-2xl text-v2-text-primary">{t('title')}</h1>
        <p className="mt-2 text-sm text-v2-text-secondary">{t(`subtitle_${me.role}`)}</p>
      </div>

      {error && <ErrorAlert error={error} title={t('error')} />}

      {isStudent && (
        <FormField label={t('grade_label')} required htmlFor="onboarding-grade">
          <Select id="onboarding-grade" value={grade} onChange={e => setGrade(e.target.value)}>
            <option value="">{t('grade_placeholder')}</option>
            {GRADES.map(g => (
              <option key={g} value={g}>
                {t('grade_option', { grade: g })}
              </option>
            ))}
          </Select>
        </FormField>
      )}

      <FormField
        label={t('subject_label')}
        required={isStudent}
        htmlFor="onboarding-subject"
        hint={isStudent ? undefined : t('subject_optional_hint')}
      >
        <Select id="onboarding-subject" value={subject} onChange={e => setSubject(e.target.value)}>
          <option value="">{t('subject_placeholder')}</option>
          {SUBJECTS.map(s => (
            <option key={s} value={s}>
              {t(`subject_${s}`)}
            </option>
          ))}
        </Select>
      </FormField>

      <button
        type="button"
        onClick={handleSubmit}
        disabled={loading || (isStudent && !grade)}
        className="w-full rounded-lg bg-v2-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-v2-accent-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus disabled:opacity-50"
      >
        {loading ? t('saving') : t('finish')}
      </button>
    </div>
  )
}
