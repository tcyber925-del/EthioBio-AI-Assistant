'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, AlertTriangle, Check, X, Loader2 } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'

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
  const [quiz, setQuiz] = useState<QuizDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updating, setUpdating] = useState(false)

  const fetchQuiz = () => {
    setLoading(true)
    fetch(`/api/admin/content/quiz/${params.id}`)
      .then(res => {
        if (!res.ok) throw new Error('Quiz not found')
        return res.json()
      })
      .then(d => { setQuiz(d); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  const updateStatus = async (newStatus: string) => {
    setUpdating(true)
    try {
      const res = await fetch(`/api/admin/content/quiz/${params.id}/status?status=${newStatus}`, { method: 'PATCH' })
      if (!res.ok) throw new Error('Failed to update status')
      setQuiz(prev => prev ? { ...prev, status: newStatus } : prev)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setUpdating(false)
    }
  }

  useEffect(() => { fetchQuiz() }, [params.id])

  if (loading) return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  if (error) return (
    <div className="text-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-red-500">{error}</p>
      <Link href="/quizzes" className="text-green-600 hover:underline mt-4 inline-block">Back to quizzes</Link>
    </div>
  )
  if (!quiz) return null

  return (
    <div>
      <Link href="/quizzes" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to quizzes
      </Link>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{quiz.title}</h1>
          <p className="text-sm text-gray-500 mt-1">Grade {quiz.grade_level} · {quiz.topic} · {quiz.question_count} questions · {quiz.model_used}</p>
        </div>
        <div className="flex gap-3">
          {quiz.status === 'draft' && (
            <>
              <button onClick={() => updateStatus('archived')} disabled={updating} className="flex items-center gap-2 px-4 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50">
                <X className="w-4 h-4" /> Reject
              </button>
              <button onClick={() => updateStatus('published')} disabled={updating} className="flex items-center gap-2 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
                <Check className="w-4 h-4" /> Approve
              </button>
            </>
          )}
          {quiz.status === 'published' && (
            <span className="px-4 py-2 text-sm bg-green-50 text-green-700 rounded-lg font-medium">Published</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-3 bg-gray-50 rounded-lg"><span className="text-xs text-gray-500">Grade</span><p className="font-semibold">Grade {quiz.grade_level}</p></div>
        <div className="p-3 bg-gray-50 rounded-lg"><span className="text-xs text-gray-500">Topic</span><p className="font-semibold">{quiz.topic}</p></div>
        <div className="p-3 bg-gray-50 rounded-lg"><span className="text-xs text-gray-500">Questions</span><p className="font-semibold">{quiz.question_count}</p></div>
        <div className="p-3 bg-gray-50 rounded-lg"><span className="text-xs text-gray-500">Status</span><p className="font-semibold capitalize">{quiz.status}</p></div>
      </div>

      {quiz.questions.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
          <p className="text-gray-400">No questions found for this quiz</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border divide-y">
          {quiz.questions.map((q, i) => (
            <div key={q.id} className="p-5">
              <div className="flex items-start gap-3">
                <span className="flex-shrink-0 w-7 h-7 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-sm font-medium">
                  {i + 1}
                </span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-gray-400 uppercase">{q.question_type}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      q.difficulty === 'easy' ? 'bg-green-50 text-green-600' :
                      q.difficulty === 'hard' ? 'bg-red-50 text-red-600' :
                      'bg-yellow-50 text-yellow-600'
                    }`}>{q.difficulty}</span>
                  </div>
                  <p className="text-gray-900 font-medium mb-2">{q.question_text}</p>
                  {q.options && (
                    <div className="space-y-1 mb-2">
                      {q.options.map((opt, j) => (
                        <div key={j} className={`text-sm px-3 py-1.5 rounded ${
                          opt.startsWith(q.correct_answer) ? 'bg-green-50 text-green-800 font-medium' : 'text-gray-600'
                        }`}>
                          {opt}
                        </div>
                      ))}
                    </div>
                  )}
                  {q.explanation && (
                    <details className="mt-2">
                      <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">Explanation</summary>
                      <p className="text-sm text-gray-600 mt-1">{q.explanation}</p>
                    </details>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-gray-400 mt-4">Created: {quiz.created_at}</p>
      {updating && <p className="text-sm text-gray-400 mt-2"><Loader2 className="w-3 h-3 inline animate-spin" /> Updating...</p>}
    </div>
  )
}
