'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, AlertTriangle, Check, X, Loader2, RefreshCw } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import { fetchWithTimeout } from '@/lib/fetch'
import { isAuthenticated } from '@/lib/auth'

interface Question {
  id: string; question_type: string; question_text: string
  options: string[] | null; correct_answer: string
  explanation: string | null; difficulty: string
}

interface QuizDetail {
  id: string; title: string; grade_level: number; topic: string
  question_count: number; status: string; model_used: string
  created_at: string; questions: Question[]
}

export default function QuizDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [quiz, setQuiz] = useState<QuizDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updating, setUpdating] = useState(false)

  const fetchQuiz = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithTimeout(`/api/admin/content/quiz/${params.id}`)
      setQuiz(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const updateStatus = async (newStatus: string) => {
    setUpdating(true)
    try {
      await fetchWithTimeout(`/api/admin/content/quiz/${params.id}/status?status=${newStatus}`, { method: 'PATCH' })
      setQuiz(prev => prev ? { ...prev, status: newStatus } : prev)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setUpdating(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchQuiz()
  }, [params.id, router])

  if (loading) return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  if (error) return (
    <div className="text-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-red-400">{error}</p>
      <div className="mt-4 flex gap-3 justify-center">
        <button onClick={fetchQuiz} className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
          <RefreshCw className="w-4 h-4 inline mr-1" /> Retry
        </button>
        <Link href="/quizzes" className="px-4 py-2 bg-card border border-border text-foreground rounded-lg text-sm hover:bg-border transition-colors">
          Back to quizzes
        </Link>
      </div>
    </div>
  )
  if (!quiz) return null

  return (
    <div>
      <Link href="/quizzes" className="flex items-center gap-2 text-sm text-foreground-muted hover:text-foreground mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to quizzes
      </Link>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{quiz.title}</h1>
          <p className="text-sm text-foreground-muted mt-1">Grade {quiz.grade_level} · {quiz.topic} · {quiz.question_count} questions · {quiz.model_used}</p>
        </div>
        <div className="flex gap-3">
          {quiz.status === 'draft' && (
            <>
              <button onClick={() => updateStatus('archived')} disabled={updating} className="flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-lg hover:bg-card disabled:opacity-50 text-foreground-muted transition-colors">
                <X className="w-4 h-4" /> Reject
              </button>
              <button onClick={() => updateStatus('published')} disabled={updating} className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50 transition-colors">
                <Check className="w-4 h-4" /> Approve
              </button>
            </>
          )}
          {quiz.status === 'published' && (
            <span className="px-4 py-2 text-sm bg-green-500/10 text-green-400 rounded-lg font-medium">Published</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-3 bg-card border border-border rounded-lg"><span className="text-xs text-foreground-muted">Grade</span><p className="font-semibold text-foreground">Grade {quiz.grade_level}</p></div>
        <div className="p-3 bg-card border border-border rounded-lg"><span className="text-xs text-foreground-muted">Topic</span><p className="font-semibold text-foreground">{quiz.topic}</p></div>
        <div className="p-3 bg-card border border-border rounded-lg"><span className="text-xs text-foreground-muted">Questions</span><p className="font-semibold text-foreground">{quiz.question_count}</p></div>
        <div className="p-3 bg-card border border-border rounded-lg"><span className="text-xs text-foreground-muted">Status</span><p className="font-semibold text-foreground capitalize">{quiz.status}</p></div>
      </div>

      {quiz.questions.length === 0 ? (
        <div className="bg-card rounded-xl border border-border p-8 text-center">
          <p className="text-foreground-muted">No questions found for this quiz</p>
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border divide-y divide-border">
          {quiz.questions.map((q, i) => (
            <div key={q.id} className="p-5">
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 w-7 h-7 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-medium">
                  {i + 1}
                </span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-foreground-muted uppercase">{q.question_type}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      q.difficulty === 'easy' ? 'bg-green-500/10 text-green-400' :
                      q.difficulty === 'hard' ? 'bg-red-500/10 text-red-400' :
                      'bg-yellow-500/10 text-yellow-400'
                    }`}>{q.difficulty}</span>
                  </div>
                  <MarkdownRenderer content={q.question_text} className="text-foreground font-medium mb-2" />
                  {q.options && (
                    <div className="space-y-1 mb-2">
                      {q.options.map((opt, j) => (
                        <div key={j} className={`text-sm px-3 py-1.5 rounded ${
                          opt.startsWith(q.correct_answer) ? 'bg-green-500/10 text-green-400 font-medium' : 'text-foreground-muted'
                        }`}>
                          {opt}
                        </div>
                      ))}
                    </div>
                  )}
                  {q.explanation && (
                    <details className="mt-2">
                      <summary className="text-xs text-foreground-muted cursor-pointer hover:text-foreground transition-colors">Explanation</summary>
                      <MarkdownRenderer content={q.explanation} className="text-sm text-foreground-muted mt-1" />
                    </details>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-foreground-muted mt-4">Created: {quiz.created_at}</p>
      {updating && <p className="text-sm text-foreground-muted mt-2"><Loader2 className="w-3 h-3 inline animate-spin" /> Updating...</p>}
    </div>
  )
}
