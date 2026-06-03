'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export default function AdminLessonDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [lesson, setLesson] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    fetchWithAuth(`/admin/content/lesson/${id}`)
      .then(setLesson)
      .catch(err => setError(err instanceof Error ? err.message : String(err)))
  }, [id])

  const toggleStatus = async () => {
    const newStatus = lesson.status === 'published' ? 'archived' : 'published'
    await fetchWithAuth(`/admin/content/lesson/${id}/status?status=${newStatus}`, { method: 'PATCH' })
    setLesson({ ...lesson, status: newStatus })
  }

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (!lesson) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <button onClick={() => router.push('/admin/content')} className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Content</button>
      <h1 className="text-2xl font-bold mb-4">{lesson.topic}</h1>
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div><strong>Grade:</strong> {lesson.grade_level}</div>
        <div><strong>Status:</strong> <span className={`px-2 py-0.5 rounded text-xs ${lesson.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{lesson.status}</span></div>
        <div><strong>Model:</strong> {lesson.model_used}</div>
        <div><strong>Created:</strong> {lesson.created_at ? new Date(lesson.created_at).toLocaleDateString() : '-'}</div>
      </div>
      <button onClick={toggleStatus} className={`px-4 py-2 rounded text-white ${lesson.status === 'published' ? 'bg-red-600' : 'bg-green-600'}`}>
        {lesson.status === 'published' ? 'Archive Lesson' : 'Publish Lesson'}
      </button>
      <div className="mt-6 space-y-4">
        <div><strong>Objective:</strong><p className="mt-1">{lesson.objective}</p></div>
        {lesson.prior_knowledge && <div><strong>Prior Knowledge:</strong><p className="mt-1">{lesson.prior_knowledge}</p></div>}
        {lesson.explanation && <div><strong>Explanation:</strong><p className="mt-1">{lesson.explanation}</p></div>}
        {lesson.activities && <div><strong>Activities:</strong><p className="mt-1 whitespace-pre-wrap">{typeof lesson.activities === 'string' ? lesson.activities : JSON.stringify(lesson.activities)}</p></div>}
        {lesson.assessment && <div><strong>Assessment:</strong><p className="mt-1">{lesson.assessment}</p></div>}
        {lesson.homework && <div><strong>Homework:</strong><p className="mt-1">{lesson.homework}</p></div>}
        {lesson.teacher_notes && <div><strong>Teacher Notes:</strong><p className="mt-1">{lesson.teacher_notes}</p></div>}
      </div>
    </div>
  )
}
