'use client'

import { useLocale, useTranslations } from 'next-intl'
import { useSubjectGrade, type SubjectOption } from '@/context/SubjectGradeContext'

const GRADES = [7, 8, 9, 10, 11, 12]

export function SubjectGradeSelector() {
  const t = useTranslations('subjectgrade')
  const locale = useLocale()
  const { grade, subject, setGrade, setSubject, availableSubjects } = useSubjectGrade()

  const subjectLabel = (s: SubjectOption) => (locale === 'am' ? s.label_am : s.label_en)

  return (
    <div
      className="flex items-center gap-2"
      role="group"
      aria-label={t('subject_selector')}
    >
      <label className="flex items-center gap-1.5 text-xs text-v2-text-secondary">
        <span className="hidden sm:inline">{t('grade_label')}</span>
        <select
          value={grade}
          onChange={(e) => setGrade(Number(e.target.value))}
          className="bg-v2-surface border border-v2-border text-v2-text-primary text-xs rounded-lg px-2 py-1.5 outline-none focus:border-v2-accent"
        >
          {GRADES.map((g) => (
            <option key={g} value={g}>
              {t('grade_label')} {g}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-1.5 text-xs text-v2-text-secondary">
        <span className="hidden sm:inline">{t('subject_label')}</span>
        <select
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="bg-v2-surface border border-v2-border text-v2-text-primary text-xs rounded-lg px-2 py-1.5 outline-none focus:border-v2-accent"
        >
          {availableSubjects.map((s) => (
            <option key={s.value} value={s.value} disabled={s.comingSoon}>
              {subjectLabel(s)}
              {s.comingSoon ? ` (${t('subject_coming_soon')})` : ''}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}
