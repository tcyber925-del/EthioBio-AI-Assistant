'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import {
  ClipboardCheck, Loader2, AlertTriangle, ArrowRight, Sparkles, ChevronDown, History,
} from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId, isAuthenticated } from '@/lib/auth'

interface QuizItem {
  id: string
  title: string
  grade_level: number
  topic: string
  question_count: number
  created_at: string
}

const QUESTION_TYPES = [
  { id: 'multiple_choice', labelKey: 'multiple_choice' },
  { id: 'true_false', labelKey: 'true_false' },
] as const

export default function QuizTakeListPage() {
  const router = useRouter()
  const t = useTranslations('quiz')
  const tc = useTranslations('common')

  const [quizzes, setQuizzes] = useState<QuizItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [genTopic, setGenTopic] = useState('')
  const [genGrade, setGenGrade] = useState(12)
  const [genCount, setGenCount] = useState(5)
  const [genTypes, setGenTypes] = useState<string[]>(['multiple_choice', 'true_false'])
  const [genModel, setGenModel] = useState('')
  const [generating, setGenerating] = useState(false)
  const [genStatus, setGenStatus] = useState<string | null>(null)
  const [genError, setGenError] = useState<string | null>(null)

  const fetchQuizzes = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchWithAuth('/api/quiz/published')
      const data = await res.json()
      setQuizzes(data.items || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchQuizzes()
  }, [router])

  const toggleType = (type: string) => {
    setGenTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type],
    )
  }

  const generateQuiz = async () => {
    if (!genTopic.trim()) return
    setGenerating(true)
    setGenStatus(null)
    setGenError(null)
    try {
      const types = genTypes.length === 0 ? ['multiple_choice', 'true_false'] : genTypes
      const res = await fetchWithAuth('/api/quiz/generate/take', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          grade_level: genGrade,
          topic: genTopic.trim(),
          question_count: genCount,
          types,
          model: genModel || undefined,
        }),
      })
      if (!res.ok) throw new Error('Generation failed to start')
      const { task_id } = await res.json()

      for (let i = 0; i < 120; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const taskRes = await fetchWithAuth(`/api/quiz/generate/status/${task_id}`)
        const task = await taskRes.json()
        if (task.status === 'completed') {
          router.push(`/quiz/take/${task.quiz_id}`)
          return
        }
        if (task.status === 'failed') {
          throw new Error(task.error || 'Generation failed')
        }
      }
      throw new Error('Generation timed out')
    } catch (err: any) {
      setGenError(err.message)
      setGenerating(false)
    } finally {
      setGenStatus(null)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardCheck className="w-6 h-6 text-v2-accent" />
        <div>
          <h1 className="text-xl font-bold text-v2-text-primary">{t('take_title')}</h1>
          <p className="text-sm text-v2-text-muted">{t('take_subtitle')}</p>
        </div>
      </div>

      <div className="rounded-[20px] border border-v2-border bg-v2-bg p-5">
        <h2 className="text-sm font-semibold text-v2-text-primary mb-4 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-v2-accent" />
          {t('generate_take_quiz')}
        </h2>
        <div className="space-y-4">
          <input
            type="text"
            value={genTopic}
            onChange={e => setGenTopic(e.target.value)}
            placeholder={t('generate_take_placeholder')}
            className="w-full px-4 py-3 border border-v2-border rounded-lg text-sm bg-v2-surface text-v2-text-primary placeholder:text-v2-text-muted/50 focus:outline-none focus:ring-1 focus:ring-v2-accent"
          />
          <div className="flex gap-3">
            <select
              value={genGrade}
              onChange={e => setGenGrade(Number(e.target.value))}
              className="flex-1 px-3 py-3 border border-v2-border rounded-lg text-sm bg-v2-bg text-v2-text-primary focus:outline-none focus:ring-1 focus:ring-v2-accent"
            >
              {[7, 8, 9, 10, 11, 12].map(g => (
                <option key={g} value={g}>{t('grade_label')} {g}</option>
              ))}
            </select>
            <div className="relative flex-1">
              <select
                value={genCount}
                onChange={e => setGenCount(Number(e.target.value))}
                className="w-full appearance-none px-3 py-3 pr-8 border border-v2-border rounded-lg text-sm bg-v2-bg text-v2-text-primary focus:outline-none focus:ring-1 focus:ring-v2-accent"
              >
                {[3, 5, 10, 15, 20].map(n => (
                  <option key={n} value={n}>{n} {t('questions').toLowerCase()}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-v2-text-muted pointer-events-none" />
            </div>
          </div>
          <div className="flex gap-2">
            {QUESTION_TYPES.map(qt => (
              <button
                key={qt.id}
                onClick={() => toggleType(qt.id)}
                className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                  genTypes.includes(qt.id)
                    ? 'bg-v2-accent/10 border-v2-accent text-v2-accent'
                    : 'border-v2-border text-v2-text-muted hover:text-v2-text-primary'
                }`}
              >
                {t(qt.labelKey)}
              </button>
            ))}
          </div>
          <button
            onClick={generateQuiz}
            disabled={generating || !genTopic.trim()}
            className="w-full px-4 py-3 bg-v2-accent text-v2-inverted rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-opacity"
          >
            {generating ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> {t('generating')}</>
            ) : (
              <><Sparkles className="w-4 h-4" /> {t('generate')}</>
            )}
          </button>
          {genError && (
            <p className="text-xs text-red-400 flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" /> {genError}
            </p>
          )}
        </div>
      </div>

      <div className="border-t border-v2-border pt-6">
        <h2 className="text-sm font-semibold text-v2-text-primary mb-3">{t('published_quizzes')}</h2>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-v2-accent" />
          </div>
        )}

        {error && (
          <div className="text-center py-8">
            <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
            <p className="text-sm text-red-400">{error}</p>
            <button onClick={fetchQuizzes} className="mt-3 px-4 py-2 bg-v2-accent text-v2-inverted rounded-lg text-xs">{tc('retry')}</button>
          </div>
        )}

        {!loading && !error && quizzes.length === 0 && (
          <div className="text-center py-8">
            <p className="text-sm text-v2-text-muted">{t('no_quizzes')}</p>
          </div>
        )}

        <div className="space-y-3">
          {quizzes.map(q => (
            <Link
              key={q.id}
              href={`/quiz/take/${q.id}`}
              className="block rounded-[20px] border border-v2-border bg-v2-bg p-5 hover:border-v2-accent/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <h3 className="font-medium text-v2-text-primary">{q.title}</h3>
                  <p className="text-sm text-v2-text-muted mt-1">
                    {t('grade_label')} {q.grade_level} &middot; {q.topic} &middot; {q.question_count} {t('questions')}
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-v2-text-muted mt-1 shrink-0" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      <div className="text-center">
        <Link
          href="/quiz/history"
          className="inline-flex items-center gap-2 px-4 py-2 text-sm text-v2-text-muted hover:text-v2-text-primary border border-v2-border rounded-lg transition-colors"
        >
          <History className="w-4 h-4" />
          {t('view_history')}
        </Link>
      </div>
    </div>
  )
}
