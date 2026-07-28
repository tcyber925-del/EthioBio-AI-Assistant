'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { ArrowLeft, Check, X, Loader2, AlertTriangle, Award } from 'lucide-react'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

interface DetailQuestion {
  id: string
  question_type: string
  question_text: string
  options: string[] | null
  correct_answer: string
  explanation: string | null
  your_answer: string
}

interface AttemptDetail {
  id: string
  quiz_id: string
  title: string
  topic: string
  grade_level: number
  score: number
  total: number
  completed_at: string | null
  questions: DetailQuestion[]
}

export default function QuizAttemptDetailPage() {
  const params = useParams()
  const router = useRouter()
  const t = useTranslations('quiz')
  const tc = useTranslations('common')

  const [attempt, setAttempt] = useState<AttemptDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAttempt = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchWithAuth(`/api/quiz/attempts/${params.id}`)
      if (!res.ok) throw new Error('Attempt not found')
      const data: AttemptDetail = await res.json()
      setAttempt(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [params.id])

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchAttempt()
  }, [fetchAttempt, router])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-6 h-6 animate-spin text-v2-accent" />
      </div>
    )
  }

  if (error || !attempt) {
    return (
      <div className="text-center py-16">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <p className="text-red-400">{error}</p>
        <div className="mt-4 flex gap-3 justify-center">
          <button onClick={fetchAttempt} className="px-4 py-2 bg-v2-accent text-v2-inverted rounded-lg text-sm">{tc('retry')}</button>
          <Link href="/quiz/history" className="px-4 py-2 border border-v2-border rounded-lg text-sm text-v2-text-muted">{t('back')}</Link>
        </div>
      </div>
    )
  }

  const roundedScore = Math.round(attempt.score)
  const scoreColor = roundedScore >= 80 ? 'text-green-400' : roundedScore >= 50 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link href="/quiz/history" className="flex items-center gap-2 text-sm text-v2-text-muted hover:text-v2-text-primary">
        <ArrowLeft className="w-4 h-4" /> {t('back')}
      </Link>

      <div className="rounded-[20px] border border-v2-border bg-v2-bg p-6 text-center">
        <Award className="w-12 h-12 text-v2-accent mx-auto mb-3" />
        <h2 className="text-xl font-bold text-v2-text-primary">{attempt.title}</h2>
        <p className="text-sm text-v2-text-muted mt-1">
          {t('grade_label')} {attempt.grade_level} &middot; {attempt.topic}
        </p>
        {attempt.completed_at && (
          <p className="text-xs text-v2-text-muted mt-1">
            {new Date(attempt.completed_at).toLocaleDateString()} {new Date(attempt.completed_at).toLocaleTimeString()}
          </p>
        )}
        <p className={`text-5xl font-bold ${scoreColor} mt-4`}>{roundedScore}%</p>
      </div>

      <div className="space-y-4">
        {attempt.questions.map((q, i) => {
          const isCorrect = q.your_answer.trim().toLowerCase() === q.correct_answer.trim().toLowerCase()
          return (
            <div
              key={q.id}
              className={`rounded-[20px] border p-5 ${
                isCorrect ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`p-1 rounded-full ${isCorrect ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {isCorrect ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                </div>
                <div className="flex-1">
                  <p className="text-xs text-v2-text-muted uppercase mb-1">
                    {t('question')} {i + 1} &middot; {q.question_type.replace(/_/g, ' ')}
                  </p>
                  <MarkdownRenderer content={q.question_text} className="text-sm text-v2-text-primary font-medium mb-2" />
                  <p className="text-xs text-v2-text-muted">
                    {t('your_answer')}: <span className={isCorrect ? 'text-green-400' : 'text-red-400'}>{q.your_answer || '(skipped)'}</span>
                  </p>
                  {!isCorrect && (
                    <p className="text-xs text-green-400 mt-1">
                      {t('correct_answer')}: {q.correct_answer}
                    </p>
                  )}
                  {q.explanation && (
                    <details className="mt-2">
                      <summary className="text-xs text-v2-text-muted cursor-pointer hover:text-v2-text-primary">
                        {t('explanation')}
                      </summary>
                      <MarkdownRenderer content={q.explanation} className="text-sm text-v2-text-muted mt-1" />
                    </details>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex gap-3 justify-center">
        <Link href="/quiz/take" className="px-6 py-3 bg-v2-accent text-v2-inverted rounded-lg text-sm font-medium">
          {t('take_another')}
        </Link>
        <Link href="/quiz/history" className="px-6 py-3 border border-v2-border rounded-lg text-sm text-v2-text-muted">
          {t('back_to_history')}
        </Link>
      </div>
    </div>
  )
}
