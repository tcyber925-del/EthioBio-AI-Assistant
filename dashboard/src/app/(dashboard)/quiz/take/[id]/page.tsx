'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import {
  ArrowLeft, Check, X, Loader2, Award, ChevronLeft, ChevronRight,
} from 'lucide-react'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import { QuizVoiceButton } from '@/components/QuizVoiceButton'
import { ErrorAlert, ErrorState } from '@/components/ui/errors'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId, isAuthenticated } from '@/lib/auth'
import { normalizeException, type AppError } from '@/lib/errors'

interface QuestionData {
  id: string
  question_type: string
  question_text: string
  options: string[] | null
  difficulty: string
}

interface QuizTakeData {
  id: string
  title: string
  grade_level: number
  topic: string
  question_count: number
  questions: QuestionData[]
}

interface AnswerFeedback {
  question_id: string
  correct: boolean
  correct_answer: string
  explanation: string | null
}

interface QuizResult {
  score: number
  total: number
  correct: number
  feedback: AnswerFeedback[]
  xp_awarded: number
  recommendations: { topic: string }[] | null
}

export default function QuizTakePage() {
  const params = useParams()
  const router = useRouter()
  const t = useTranslations('quiz')

  const [quiz, setQuiz] = useState<QuizTakeData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)

  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<QuizResult | null>(null)

  const fetchQuiz = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchWithAuth(`/api/quiz/${params.id}/take`)
      if (!res.ok) throw { category: 'not_found', retryable: false, params: {} }
      const data: QuizTakeData = await res.json()
      setQuiz(data)
    } catch (err) {
      setError(normalizeException(err))
    } finally {
      setLoading(false)
    }
  }, [params.id])

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchQuiz()
  }, [fetchQuiz, router])

  const isCorrectAnswer = (option: string, _correctKey: string) => {
    const letter = option.charAt(0)
    return letter === _correctKey
  }

  const setAnswer = (questionId: string, value: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }))
  }

  const allAnswered = quiz && quiz.questions.every(q => answers[q.id]?.trim())

  const submitQuiz = async () => {
    if (!quiz || !allAnswered) return
    setSubmitting(true)
    try {
      const res = await fetchWithAuth('/api/quiz/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quiz_id: quiz.id,
          user_id: getUserId(),
          answers: quiz.questions.map(q => ({
            question_id: q.id,
            answer: answers[q.id] || '',
          })),
        }),
      })
      if (!res.ok) throw { category: 'server', retryable: true, params: {} }
      const data: QuizResult = await res.json()
      setResult(data)
    } catch (err) {
      setError(normalizeException(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-6 h-6 animate-spin text-v2-accent" />
      </div>
    )
  }

  if (error && !quiz) {
    return (
      <div>
        <Link href="/ask" className="flex items-center gap-2 text-sm text-v2-text-muted hover:text-v2-text-primary">
          <ArrowLeft className="w-4 h-4" /> {t('back')}
        </Link>
        <ErrorState error={error} onRetry={() => void fetchQuiz()} retrying={loading} />
      </div>
    )
  }

  if (result && quiz) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <Link href="/ask" className="flex items-center gap-2 text-sm text-v2-text-muted hover:text-v2-text-primary">
          <ArrowLeft className="w-4 h-4" /> {t('back')}
        </Link>

        <div className="rounded-[20px] border border-v2-border bg-v2-bg p-6 text-center">
          <Award className="w-12 h-12 text-v2-accent mx-auto mb-3" />
          <h2 className="text-2xl font-bold text-v2-text-primary">{t('result_title')}</h2>
          <p className="text-5xl font-bold text-v2-accent mt-4">{Math.round(result.score)}%</p>
          <p className="text-v2-text-muted mt-1">
            {result.correct}/{result.total} {t('correct')}
          </p>
          {result.xp_awarded > 0 && (
            <p className="text-sm text-v2-accent mt-2">+{result.xp_awarded} XP</p>
          )}
        </div>

        <div className="space-y-4">
          {result.feedback.map((fb, i) => {
            const q = quiz.questions[i]
            if (!q) return null
            return (
              <div
                key={fb.question_id}
                className={`rounded-[20px] border p-5 ${
                  fb.correct ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-1 rounded-full ${fb.correct ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {fb.correct ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-xs text-v2-text-muted uppercase mb-1">
                      {t('question')} {i + 1} &middot; {q.question_type.replace('_', ' ')}
                    </p>
                    <MarkdownRenderer content={q.question_text} className="text-sm text-v2-text-primary font-medium mb-2" />
                    <p className="text-xs text-v2-text-muted">
                      {t('your_answer')}: <span className={fb.correct ? 'text-green-400' : 'text-red-400'}>{answers[q.id]}</span>
                    </p>
                    {!fb.correct && (
                      <p className="text-xs text-green-400 mt-1">
                        {t('correct_answer')}: {fb.correct_answer}
                      </p>
                    )}
                    {fb.explanation && (
                      <details className="mt-2">
                        <summary className="text-xs text-v2-text-muted cursor-pointer hover:text-v2-text-primary">
                          {t('explanation')}
                        </summary>
                        <MarkdownRenderer content={fb.explanation} className="text-sm text-v2-text-muted mt-1" />
                      </details>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        <div className="flex gap-3 justify-center">
          <Link
            href="/ask"
            className="px-6 py-3 bg-v2-accent text-v2-inverted rounded-lg text-sm font-medium"
          >
            {t('continue_learning')}
          </Link>
          {result.recommendations && result.recommendations.length > 0 && (
            <Link
              href="/ask"
              className="px-6 py-3 border border-v2-border rounded-lg text-sm text-v2-text-muted"
            >
              {t('retry_weak_topics')}
            </Link>
          )}
        </div>
      </div>
    )
  }

  if (!quiz) return null

  const question = quiz.questions[currentIdx]
  if (!question) return null

  const isMcOrTf = question.question_type === 'multiple_choice' || question.question_type === 'true_false'
  const selectedAnswer = answers[question.id] || ''

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link href="/ask" className="flex items-center gap-2 text-sm text-v2-text-muted hover:text-v2-text-primary">
        <ArrowLeft className="w-4 h-4" /> {t('back')}
      </Link>

      {error && <ErrorAlert error={error} />}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-v2-text-primary">{quiz.title}</h1>
          <p className="text-sm text-v2-text-muted">{t('grade_label')} {quiz.grade_level} &middot; {quiz.topic}</p>
        </div>
        <span className="text-sm text-v2-text-muted font-mono">
          {currentIdx + 1}/{quiz.question_count}
        </span>
      </div>

      <div className="w-full bg-v2-border rounded-full h-1.5">
        <div
          className="bg-v2-accent h-1.5 rounded-full transition-all"
          style={{ width: `${((currentIdx + 1) / quiz.question_count) * 100}%` }}
        />
      </div>

      <div className="rounded-[20px] border border-v2-border bg-v2-bg p-6">
        <p className="text-xs text-v2-text-muted uppercase mb-1">
          {question.question_type.replace(/_/g, ' ')}
        </p>
        <MarkdownRenderer content={question.question_text} className="text-base text-v2-text-primary font-medium mb-6" />

        {isMcOrTf && question.options && (
          <div className="space-y-2">
            {question.options.map((opt, i) => {
              const letter = String.fromCharCode(65 + i)
              const isSelected = selectedAnswer === letter
              return (
                <button
                  key={opt}
                  onClick={() => setAnswer(question.id, letter)}
                  className={`w-full text-left px-4 py-3 rounded-lg text-sm border transition-all ${
                    isSelected
                      ? 'border-v2-accent bg-v2-accent/10 text-v2-accent font-medium'
                      : 'border-v2-border text-v2-text-primary hover:border-v2-accent/50'
                  }`}
                >
                  <span className="font-mono mr-2">{letter}.</span>
                  {opt.replace(/^[A-Z][.\)]\s*/, '')}
                </button>
              )
            })}
          </div>
        )}

        {!isMcOrTf && (
          <div className="flex gap-2">
            <input
              type="text"
              value={selectedAnswer}
              onChange={e => setAnswer(question.id, e.target.value)}
              placeholder={t('answer_placeholder')}
              className="flex-1 px-4 py-3 border border-v2-border rounded-lg text-sm bg-v2-surface text-v2-text-primary placeholder:text-v2-text-muted/50 focus:outline-none focus:ring-1 focus:ring-v2-accent"
            />
            <QuizVoiceButton
              onTranscript={(text) => setAnswer(question.id, text)}
              onError={console.error}
              disabled={submitting}
            />
          </div>
        )}
      </div>

      <div className="flex justify-between">
        <button
          onClick={() => setCurrentIdx(i => Math.max(0, i - 1))}
          disabled={currentIdx === 0}
          className="flex items-center gap-1 px-4 py-2 text-sm text-v2-text-muted hover:text-v2-text-primary disabled:opacity-30"
        >
          <ChevronLeft className="w-4 h-4" /> {t('previous')}
        </button>

        {currentIdx < quiz.question_count - 1 ? (
          <button
            onClick={() => setCurrentIdx(i => i + 1)}
            className="flex items-center gap-1 px-4 py-2 text-sm text-v2-accent hover:text-v2-accent/80"
          >
            {t('next')} <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={submitQuiz}
            disabled={!allAnswered || submitting}
            className="flex items-center gap-2 px-6 py-2 bg-v2-accent text-v2-inverted rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> {t('submitting')}</> : t('submit')}
          </button>
        )}
      </div>

      <div className="flex justify-center gap-1.5">
        {quiz.questions.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrentIdx(i)}
            className={`w-2.5 h-2.5 rounded-full transition-colors ${
              i === currentIdx ? 'bg-v2-accent' : answers[quiz.questions[i].id] ? 'bg-v2-accent/40' : 'bg-v2-border'
            }`}
          />
        ))}
      </div>
    </div>
  )
}
