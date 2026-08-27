'use client'

import { useLocale, useTranslations } from 'next-intl'
import { useSubjectGrade, type SubjectOption } from '@/context/SubjectGradeContext'

export function SubjectSelect({ className }: { className?: string }) {
  const t = useTranslations('subjectgrade')
  const locale = useLocale()
  const { subject, setSubject, availableSubjects } = useSubjectGrade()

  const label = (s: SubjectOption) => (locale === 'am' ? s.label_am : s.label_en)

  return (
    <label
      className={`flex items-center gap-1.5 text-xs text-v2-text-secondary ${className ?? ''}`}
    >
      <span className="hidden sm:inline">{t('subject_label')}</span>
      <select
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        className="bg-v2-surface border border-v2-border text-v2-text-primary text-xs rounded-lg px-2 py-1.5 outline-none focus:border-v2-accent"
      >
        {availableSubjects.map((s) => (
          <option key={s.value} value={s.value} disabled={s.comingSoon}>
            {label(s)}
            {s.comingSoon ? ` (${t('subject_coming_soon')})` : ''}
          </option>
        ))}
      </select>
    </label>
  )
}
