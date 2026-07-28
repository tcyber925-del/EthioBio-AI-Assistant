'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { History, Loader2, AlertTriangle, Check, X, ArrowRight, Award } from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

interface AttemptItem {
  id: string
  quiz_id: string
  title: string
  topic: string
  grade_level: number
  score: number
  total: number
  correct: number
  completed_at: string
}

export default function QuizHistoryPage() {
  const router = useRouter()
  const t = useTranslations('quiz')
  const tc = useTranslations('common')

  const [attempts, setAttempts] = useState<AttemptItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAttempts = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchWithAuth('/api/quiz/attempts')
      const data = await res.json()
      setAttempts(data.items || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchAttempts()
  }, [router])

  const scoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 50) return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <History className="w-6 h-6 text-v2-accent" />
        <div>
          <h1 className="text-xl font-bold text-v2-text-primary">{t('history_title')}</h1>
          <p className="text-sm text-v2-text-muted">{t('history_subtitle')}</p>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-v2-accent" />
        </div>
      )}

      {error && (
        <div className="text-center py-16">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-red-400">{error}</p>
          <button onClick={fetchAttempts} className="mt-4 px-4 py-2 bg-v2-accent text-v2-inverted rounded-lg text-sm">{tc('retry')}</button>
        </div>
      )}

      {!loading && !error && attempts.length === 0 && (
        <div className="text-center py-16">
          <Award className="w-12 h-12 text-v2-text-muted/20 mx-auto mb-3" />
          <p className="text-v2-text-muted">{t('no_attempts')}</p>
          <Link href="/quiz/take" className="inline-block mt-4 px-4 py-2 bg-v2-accent text-v2-inverted rounded-lg text-sm">
            {t('take_first_quiz')}
          </Link>
        </div>
      )}

      <div className="space-y-3">
        {attempts.map(a => (
          <Link
            key={a.id}
            href={`/quiz/history/${a.id}`}
            className="block rounded-[20px] border border-v2-border bg-v2-bg p-5 hover:border-v2-accent/50 transition-colors"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-v2-text-primary truncate">{a.title}</h3>
                <p className="text-sm text-v2-text-muted mt-1">
                  {t('grade_label')} {a.grade_level} &middot; {a.topic}
                </p>
                <p className="text-xs text-v2-text-muted mt-1">
                  {a.completed_at ? new Date(a.completed_at).toLocaleDateString() : ''}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className={`text-2xl font-bold ${scoreColor(a.score)}`}>
                  {Math.round(a.score)}%
                </p>
                <p className="text-xs text-v2-text-muted">
                  {a.correct}/{a.total} {t('correct')}
                </p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
