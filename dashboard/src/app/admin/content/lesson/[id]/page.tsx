'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export const dynamic = 'force-dynamic'

interface LessonData {
  id: string
  topic: string
  grade_level: number
  status: string
  model_used?: string
  created_at?: string
  objective?: string
  prior_knowledge?: string
  explanation?: string
  activities?: string | string[]
  assessment?: string
  homework?: string
  teacher_notes?: string
}

export default function AdminLessonDetailPage() {
  const { id } = useParams<{ id: string }>()
  const locale = useLocale()
  const tc = useTranslations('admin.content')
  const tcommon = useTranslations('common')
  const [lesson, setLesson] = useState<LessonData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  useEffect(() => {
    fetchWithAuth(`/api/admin/content/lesson/${id}`)
      .then(setLesson)
      .catch(err => setError(err instanceof Error ? err.message : String(err)))
  }, [id])

  const toggleStatus = async () => {
    if (!lesson) return
    const newStatus = lesson.status === 'published' ? 'archived' : 'published'
    await fetchWithAuth(`/api/admin/content/lesson/${id}/status?status=${newStatus}`, { method: 'PATCH' })
    setLesson({ ...lesson, status: newStatus })
  }

  if (error) return <p className="text-red-600">{tcommon('error')}: {error}</p>
  if (!lesson) return <p className="text-gray-500">{tcommon('loading')}</p>

  return (
    <div>
      <button onClick={() => router.push('/admin/content')} className="text-blue-600 hover:underline mb-4 inline-block">&larr; {tc('back_to_content')}</button>
      <h1 className="text-2xl font-bold mb-4">{lesson.topic}</h1>
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div><strong>{tc('grade_label')}</strong> {lesson.grade_level}</div>
        <div><strong>{tc('status_label')}</strong> <span className={`px-2 py-0.5 rounded text-xs ${lesson.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{lesson.status}</span></div>
        <div><strong>{tc('model')}</strong> {lesson.model_used}</div>
        <div><strong>{tc('created_label')}</strong> {lesson.created_at ? new Date(lesson.created_at).toLocaleDateString(locale) : '-'}</div>
      </div>
      <button onClick={toggleStatus} className={`px-4 py-2 rounded text-white ${lesson.status === 'published' ? 'bg-red-600' : 'bg-green-600'}`}>
        {lesson.status === 'published' ? tc('archive_lesson') : tc('publish_lesson')}
      </button>
      <div className="mt-6 space-y-4">
        <div><strong>{tc('objective')}:</strong><p className="mt-1">{lesson.objective}</p></div>
        {lesson.prior_knowledge && <div><strong>{tc('prior_knowledge')}:</strong><p className="mt-1">{lesson.prior_knowledge}</p></div>}
        {lesson.explanation && <div><strong>{tc('explanation')}:</strong><p className="mt-1">{lesson.explanation}</p></div>}
        {lesson.activities && <div><strong>{tc('activities')}:</strong><p className="mt-1 whitespace-pre-wrap">{typeof lesson.activities === 'string' ? lesson.activities : JSON.stringify(lesson.activities)}</p></div>}
        {lesson.assessment && <div><strong>{tc('assessment')}:</strong><p className="mt-1">{lesson.assessment}</p></div>}
        {lesson.homework && <div><strong>{tc('homework')}:</strong><p className="mt-1">{lesson.homework}</p></div>}
        {lesson.teacher_notes && <div><strong>{tc('teacher_notes')}:</strong><p className="mt-1">{lesson.teacher_notes}</p></div>}
      </div>
    </div>
  )
}
