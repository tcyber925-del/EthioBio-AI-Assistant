'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, AlertTriangle, Check, X, Loader2 } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'

interface LessonDetail {
  id: string; topic: string; grade_level: number
  objective: string; prior_knowledge: string | null
  explanation: string; activities: any[]
  assessment: string; homework: string | null; teacher_notes: string | null
  status: string; model_used: string; created_at: string
}

export default function LessonDetailPage() {
  const params = useParams()
  const [lesson, setLesson] = useState<LessonDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updating, setUpdating] = useState(false)

  const fetchLesson = () => {
    setLoading(true)
    fetch(`/api/admin/content/lesson/${params.id}`)
      .then(res => {
        if (!res.ok) throw new Error('Lesson plan not found')
        return res.json()
      })
      .then(d => { setLesson(d); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  const updateStatus = async (newStatus: string) => {
    setUpdating(true)
    try {
      const res = await fetch(`/api/admin/content/lesson/${params.id}/status?status=${newStatus}`, { method: 'PATCH' })
      if (!res.ok) throw new Error('Failed to update status')
      setLesson(prev => prev ? { ...prev, status: newStatus } : prev)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setUpdating(false)
    }
  }

  useEffect(() => { fetchLesson() }, [params.id])

  if (loading) return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  if (error) return (
    <div className="text-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-red-500">{error}</p>
      <Link href="/lessons" className="text-green-600 hover:underline mt-4 inline-block">Back to lesson plans</Link>
    </div>
  )
  if (!lesson) return null

  return (
    <div>
      <Link href="/lessons" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to lesson plans
      </Link>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{lesson.topic}</h1>
          <p className="text-sm text-gray-500 mt-1">Grade {lesson.grade_level} · {lesson.status} · {lesson.model_used}</p>
        </div>
        <div className="flex gap-3">
          {lesson.status === 'draft' && (
            <>
              <button onClick={() => updateStatus('archived')} disabled={updating} className="flex items-center gap-2 px-4 py-2 text-sm border rounded-lg hover:bg-gray-50 disabled:opacity-50">
                <X className="w-4 h-4" /> Reject
              </button>
              <button onClick={() => updateStatus('published')} disabled={updating} className="flex items-center gap-2 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
                <Check className="w-4 h-4" /> Approve
              </button>
            </>
          )}
          {lesson.status === 'published' && (
            <span className="px-4 py-2 text-sm bg-green-50 text-green-700 rounded-lg font-medium">Published</span>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-6 space-y-6">
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-1">Objective</h3>
          <p className="text-gray-900">{lesson.objective}</p>
        </div>
        {lesson.prior_knowledge && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Prior Knowledge</h3>
            <p className="text-gray-900 text-sm">{lesson.prior_knowledge}</p>
          </div>
        )}
        {lesson.explanation && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Explanation</h3>
            <p className="text-gray-900 text-sm leading-relaxed whitespace-pre-wrap">{lesson.explanation}</p>
          </div>
        )}
        {lesson.activities && lesson.activities.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-2">Activities ({lesson.activities.length})</h3>
            <div className="space-y-2">
              {lesson.activities.map((a: any, i: number) => (
                <div key={i} className="p-3 bg-gray-50 rounded-lg text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{a.name}</span>
                    <span className="text-gray-400 text-xs">({a.duration_minutes}min · {a.type})</span>
                  </div>
                  <p className="text-gray-600 mt-1">{a.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}
        {lesson.assessment && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Assessment</h3>
            <p className="text-gray-900 text-sm whitespace-pre-wrap">{lesson.assessment}</p>
          </div>
        )}
        {lesson.homework && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Homework</h3>
            <p className="text-gray-900 text-sm whitespace-pre-wrap">{lesson.homework}</p>
          </div>
        )}
        {lesson.teacher_notes && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">Teacher Notes</h3>
            <p className="text-gray-900 text-sm italic whitespace-pre-wrap">{lesson.teacher_notes}</p>
          </div>
        )}
        <p className="text-xs text-gray-400 pt-4 border-t">Created: {lesson.created_at}</p>
      </div>
      {updating && <p className="text-sm text-gray-400 mt-2"><Loader2 className="w-3 h-3 inline animate-spin" /> Updating...</p>}
    </div>
  )
}
