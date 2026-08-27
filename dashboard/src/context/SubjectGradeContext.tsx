'use client'

import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

export interface SubjectOption {
  value: string
  label_en: string
  label_am: string
  comingSoon: boolean
}

export const AVAILABLE_SUBJECTS: SubjectOption[] = [
  { value: 'biology', label_en: 'Biology', label_am: 'ባዮሎጂ', comingSoon: false },
  { value: 'chemistry', label_en: 'Chemistry', label_am: 'ኬሚስትሪ', comingSoon: true },
  { value: 'physics', label_en: 'Physics', label_am: 'ፊዚክስ', comingSoon: true },
  { value: 'mathematics', label_en: 'Mathematics', label_am: 'ሂሳብ', comingSoon: true },
]

const STORAGE_KEY = 'ethiosci_subject_grade'

export interface SubjectGradeContextType {
  grade: number
  subject: string
  setGrade: (grade: number) => void
  setSubject: (subject: string) => void
  availableSubjects: SubjectOption[]
}

const SubjectGradeContext = createContext<SubjectGradeContextType | null>(null)

export function SubjectGradeProvider({ children }: { children: React.ReactNode }) {
  const [grade, setGradeState] = useState<number>(9)
  const [subject, setSubjectState] = useState<string>('biology')
  const hydrated = useRef(false)

  const persist = useCallback((nextGrade: number, nextSubject: string) => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ grade: nextGrade, subject: nextSubject }),
      )
    } catch {
      // localStorage unavailable — non-fatal
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      // 1. Seed from /auth/me when the user has a stored preference.
      try {
        const res = await fetch('/auth/me', { credentials: 'include' })
        if (res.ok) {
          const me = await res.json()
          if (!cancelled) {
            if (typeof me.grade_level === 'number') setGradeState(me.grade_level)
            if (typeof me.subject === 'string' && me.subject) setSubjectState(me.subject)
          }
        }
      } catch {
        // backend unreachable — keep defaults
      }
      // 2. Override from localStorage so the user's last selection wins.
      try {
        const raw = localStorage.getItem(STORAGE_KEY)
        if (raw) {
          const parsed = JSON.parse(raw)
          if (!cancelled) {
            if (typeof parsed.grade === 'number') setGradeState(parsed.grade)
            if (typeof parsed.subject === 'string' && parsed.subject) {
              setSubjectState(parsed.subject)
            }
          }
        }
      } catch {
        // ignore malformed storage
      }
      if (!cancelled) hydrated.current = true
    })()
  }, [])

  const setGrade = useCallback(
    (nextGrade: number) => {
      setGradeState(nextGrade)
      persist(nextGrade, subject)
    },
    [persist, subject],
  )

  const setSubject = useCallback(
    (nextSubject: string) => {
      setSubjectState(nextSubject)
      persist(grade, nextSubject)
    },
    [persist, grade],
  )

  return (
    <SubjectGradeContext.Provider
      value={{ grade, subject, setGrade, setSubject, availableSubjects: AVAILABLE_SUBJECTS }}
    >
      {children}
    </SubjectGradeContext.Provider>
  )
}

export function useSubjectGrade(): SubjectGradeContextType {
  const ctx = useContext(SubjectGradeContext)
  if (!ctx) {
    throw new Error('useSubjectGrade must be used within a SubjectGradeProvider')
  }
  return ctx
}
