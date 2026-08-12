'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { ErrorState } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

export const dynamic = 'force-dynamic'

interface Period {
  name: string; duration_minutes: number
  objective?: string; description: string; activity_type: string
  teacher_activity?: string; student_activity?: string
  materials_needed?: string[]
}
interface ExitTicketQuestion {
  question_type: string; question_text: string
  options?: string[]; correct_answer: string; explanation?: string
}
interface DifferentiationActivity {
  group: string; description: string; duration_minutes: number
}
interface DiagramSuggestion {
  title: string; description: string; diagram_type: string
}
interface MisconceptionActivity {
  misconception: string; activity_name: string
  description: string; duration_minutes: number; activity_type: string
}
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
  periods?: Period[]
  exit_ticket?: ExitTicketQuestion[]
  differentiation?: DifferentiationActivity[]
  diagram_suggestions?: DiagramSuggestion[]
  misconception_activities?: MisconceptionActivity[]
}

export default function AdminLessonDetailPage() {
  const { id } = useParams<{ id: string }>()
  const locale = useLocale()
  const tc = useTranslations('admin.content')
  const tcommon = useTranslations('common')
  const [lesson, setLesson] = useState<LessonData | null>(null)
  const [error, setError] = useState<AppError | null>(null)
  const router = useRouter()

  const load = useCallback(async () => {
    try {
      const response = await fetchWithAuth(`/api/admin/content/lesson/${id}`)
      setLesson(await response.json())
    } catch (err) {
      setError(normalizeException(err))
    }
  }, [id])

  useEffect(() => { load() }, [load])

  const toggleStatus = async () => {
    if (!lesson) return
    const newStatus = lesson.status === 'published' ? 'archived' : 'published'
    await fetchWithAuth(`/api/admin/content/lesson/${id}/status?status=${newStatus}`, { method: 'PATCH' })
    setLesson({ ...lesson, status: newStatus })
  }

  if (error) return <ErrorState error={error} onRetry={() => void load()} />
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
        {lesson.periods && lesson.periods.length > 0 && (
          <div><strong>{tc('periods')}:</strong>
            {lesson.periods.map((p, i) => (
              <div key={i} className="mt-1 ml-2 p-2 bg-gray-50 rounded text-sm border-l-2 border-blue-400">
                <p className="font-medium">{p.name} ({p.duration_minutes}min)</p>
                {p.objective && <p className="text-xs text-gray-500">Objective: {p.objective}</p>}
                <p className="text-xs">{p.description}</p>
                {p.teacher_activity && <p className="text-xs text-gray-500">Teacher: {p.teacher_activity}</p>}
                {p.student_activity && <p className="text-xs text-gray-500">Students: {p.student_activity}</p>}
                {p.materials_needed && <p className="text-xs text-gray-500">Materials: {p.materials_needed.join(', ')}</p>}
              </div>
            ))}
          </div>
        )}
        {lesson.assessment && <div><strong>{tc('assessment')}:</strong><p className="mt-1">{lesson.assessment}</p></div>}
        {lesson.homework && <div><strong>{tc('homework')}:</strong><p className="mt-1">{lesson.homework}</p></div>}
        {lesson.teacher_notes && <div><strong>{tc('teacher_notes')}:</strong><p className="mt-1">{lesson.teacher_notes}</p></div>}
        {lesson.exit_ticket && lesson.exit_ticket.length > 0 && (
          <div className="mt-4"><strong>Exit Ticket:</strong>
            {lesson.exit_ticket.map((q, i) => (
              <p key={i} className="mt-1 text-sm">Q{i+1}. {q.question_text} ({q.question_type}) — ✓ {q.correct_answer}</p>
            ))}
          </div>
        )}
        {lesson.differentiation && lesson.differentiation.length > 0 && (
          <div className="mt-4"><strong>Differentiated Activities:</strong>
            {lesson.differentiation.map((d, i) => (
              <p key={i} className="mt-1 text-sm">{d.group}: {d.description} ({d.duration_minutes}min)</p>
            ))}
          </div>
        )}
        {lesson.diagram_suggestions && lesson.diagram_suggestions.length > 0 && (
          <div className="mt-4"><strong>Diagram Suggestions:</strong>
            {lesson.diagram_suggestions.map((d, i) => (
              <p key={i} className="mt-1 text-sm">{d.title} ({d.diagram_type}) — {d.description}</p>
            ))}
          </div>
        )}
        {lesson.misconception_activities && lesson.misconception_activities.length > 0 && (
          <div className="mt-4"><strong>Misconception Activities:</strong>
            {lesson.misconception_activities.map((a, i) => (
              <p key={i} className="mt-1 text-sm">{a.activity_name} ({a.activity_type}, {a.duration_minutes}min) — addressing: {a.misconception}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
