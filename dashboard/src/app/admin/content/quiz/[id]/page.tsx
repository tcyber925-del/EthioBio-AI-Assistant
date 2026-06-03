'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export default function AdminQuizDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [quiz, setQuiz] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    fetchWithAuth(`/admin/content/quiz/${id}`)
      .then(res => res.json())
      .then(setQuiz)
      .catch(err => setError(err.message))
  }, [id])

  const toggleStatus = async () => {
    const newStatus = quiz.status === 'published' ? 'archived' : 'published'
    await fetchWithAuth(`/admin/content/quiz/${id}/status?status=${newStatus}`, { method: 'PATCH' })
    setQuiz({ ...quiz, status: newStatus })
  }

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!quiz) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <button onClick={() => router.push('/admin/content')} className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Content</button>
      <h1 className="text-2xl font-bold mb-4">{quiz.title}</h1>
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div><strong>Grade:</strong> {quiz.grade_level}</div>
        <div><strong>Topic:</strong> {quiz.topic}</div>
        <div><strong>Status:</strong> <span className={`px-2 py-0.5 rounded text-xs ${quiz.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{quiz.status}</span></div>
        <div><strong>Model:</strong> {quiz.model_used}</div>
        <div><strong>Questions:</strong> {quiz.question_count}</div>
        <div><strong>Created:</strong> {quiz.created_at ? new Date(quiz.created_at).toLocaleDateString() : '-'}</div>
      </div>
      <button onClick={toggleStatus} className={`px-4 py-2 rounded text-white ${quiz.status === 'published' ? 'bg-red-600' : 'bg-green-600'}`}>
        {quiz.status === 'published' ? 'Archive Quiz' : 'Publish Quiz'}
      </button>
      <h2 className="text-xl font-semibold mt-8 mb-4">Questions</h2>
      {quiz.questions?.map((q: any, i: number) => (
        <div key={q.id} className="border rounded p-4 mb-3">
          <p className="font-medium">{i + 1}. {q.question_text}</p>
          <p className="text-sm text-gray-500 mt-1">Type: {q.question_type} | Difficulty: {q.difficulty}</p>
          {q.options?.length > 0 && (
            <ul className="mt-2 space-y-1">
              {q.options.map((opt: string, j: number) => (
                <li key={j} className={`text-sm ${opt === q.correct_answer ? 'text-green-700 font-medium' : ''}`}>
                  {opt === q.correct_answer ? '✓ ' : ''}{opt}
                </li>
              ))}
            </ul>
          )}
          {q.explanation && <p className="text-sm text-gray-600 mt-2 italic">{q.explanation}</p>}
        </div>
      ))}
    </div>
  )
}
