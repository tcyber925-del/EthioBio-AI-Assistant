'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { ArrowLeft, AlertTriangle, Check, X, Loader2, RefreshCw } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

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
interface Period {
  name: string; duration_minutes: number
  objective?: string; description: string; activity_type: string
  teacher_activity?: string; student_activity?: string
  materials_needed?: string[]
}
interface LessonDetail {
  id: string; topic: string; grade_level: number
  objective: string; prior_knowledge: string | null
  explanation: string; activities: any[]
  assessment: string; homework: string | null; teacher_notes: string | null
  status: string; model_used: string; created_at: string
  periods?: Period[]
  exit_ticket?: ExitTicketQuestion[]
  differentiation?: DifferentiationActivity[]
  diagram_suggestions?: DiagramSuggestion[]
  misconception_activities?: MisconceptionActivity[]
  classroom_context?: any
}

export default function LessonDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [lesson, setLesson] = useState<LessonDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [updating, setUpdating] = useState(false)
  const t = useTranslations('lesson')
  const tc = useTranslations('common')

  const fetchLesson = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithAuth(`/api/lesson-plan/${params.id}`)
      setLesson(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const updateStatus = async (newStatus: string) => {
    setUpdating(true)
    try {
      await fetchWithAuth(`/api/lesson-plan/${params.id}/rate?status=${newStatus}`, { method: 'PATCH' })
      setLesson(prev => prev ? { ...prev, status: newStatus } : prev)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setUpdating(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchLesson()
  }, [params.id, router])

  if (loading) return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  if (error) return (
    <div className="text-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-red-400">{error}</p>
      <div className="mt-4 flex gap-3 justify-center">
        <button onClick={fetchLesson} className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
          <RefreshCw className="w-4 h-4 inline mr-1" /> {tc('retry')}
        </button>
        <Link href="/lessons" className="px-4 py-2 bg-card border border-border text-foreground rounded-lg text-sm hover:bg-border transition-colors">
          {t('back')}
        </Link>
      </div>
    </div>
  )
  if (!lesson) return null

  return (
    <div>
      <Link href="/lessons" className="flex items-center gap-2 text-sm text-foreground-muted hover:text-foreground mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" /> {t('back')}
      </Link>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{lesson.topic}</h1>
          <p className="text-sm text-foreground-muted mt-1">{t('col_grade')} {lesson.grade_level} · {lesson.status} · {lesson.model_used}</p>
        </div>
        <div className="flex gap-3">
          {lesson.status === 'draft' && (
            <>
              <button onClick={() => updateStatus('archived')} disabled={updating} className="flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-lg hover:bg-card disabled:opacity-50 text-foreground-muted transition-colors">
                <X className="w-4 h-4" /> {t('reject')}
              </button>
              <button onClick={() => updateStatus('published')} disabled={updating} className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50 transition-colors">
                <Check className="w-4 h-4" /> {t('approve')}
              </button>
            </>
          )}
          {lesson.status === 'published' && (
            <span className="px-4 py-2 text-sm bg-green-500/10 text-green-400 rounded-lg font-medium">{t('published')}</span>
          )}
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border p-6 space-y-6">
        <div>
          <h3 className="text-sm font-medium text-foreground-muted mb-1">{t('details_objective')}</h3>
          <MarkdownRenderer content={lesson.objective} className="text-foreground" />
        </div>
        {lesson.prior_knowledge && (
          <div>
            <h3 className="text-sm font-medium text-foreground-muted mb-1">{t('details_prior_knowledge')}</h3>
            <MarkdownRenderer content={lesson.prior_knowledge} className="text-foreground text-sm" />
          </div>
        )}
        {lesson.explanation && (
          <div>
            <h3 className="text-sm font-medium text-foreground-muted mb-1">{t('details_explanation')}</h3>
            <MarkdownRenderer content={lesson.explanation} className="text-foreground text-sm" />
          </div>
        )}
        {lesson.activities && lesson.activities.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-foreground-muted mb-2">{t('details_activities')} ({lesson.activities.length})</h3>
            <div className="space-y-2">
              {lesson.activities.map((a: any, i: number) => (
                <div key={i} className="p-3 bg-background-secondary rounded-lg text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground">{a.name}</span>
                    <span className="text-foreground-muted text-xs">({a.duration_minutes}min · {a.type})</span>
                  </div>
                  <p className="text-foreground-muted mt-1">{a.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}
        {lesson.periods && lesson.periods.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-foreground-muted mb-2">{t('details_periods')} ({lesson.periods.length})</h3>
            <div className="space-y-3">
              {lesson.periods.map((p, i) => (
                <div key={i} className="p-3 bg-background-secondary rounded-lg text-sm border-l-4 border-primary">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-foreground">{p.name}</span>
                    <span className="text-foreground-muted text-xs">({p.duration_minutes}min · {p.activity_type})</span>
                  </div>
                  {p.objective && <p className="text-xs text-foreground-muted mb-1"><span className="font-medium">Objective:</span> {p.objective}</p>}
                  <p className="text-foreground-muted">{p.description}</p>
                  <div className="mt-1 grid grid-cols-2 gap-1 text-xs text-foreground-muted">
                    {p.teacher_activity && <p><span className="font-medium">Teacher:</span> {p.teacher_activity}</p>}
                    {p.student_activity && <p><span className="font-medium">Students:</span> {p.student_activity}</p>}
                  </div>
                  {p.materials_needed && p.materials_needed.length > 0 && (
                    <p className="text-xs text-foreground-muted mt-1">
                      <span className="font-medium">Materials:</span> {p.materials_needed.join(', ')}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {lesson.assessment && (
          <div>
            <h3 className="text-sm font-medium text-foreground-muted mb-1">{t('details_assessment')}</h3>
            <MarkdownRenderer content={lesson.assessment} className="text-foreground text-sm" />
          </div>
        )}
        {lesson.homework && (
          <div>
            <h3 className="text-sm font-medium text-foreground-muted mb-1">{t('details_homework')}</h3>
            <MarkdownRenderer content={lesson.homework} className="text-foreground text-sm" />
          </div>
        )}
        {lesson.teacher_notes && (
          <div>
            <h3 className="text-sm font-medium text-foreground-muted mb-1">{t('details_teacher_notes')}</h3>
            <MarkdownRenderer content={lesson.teacher_notes} className="text-foreground text-sm text-foreground-muted italic" />
          </div>
        )}

        {lesson.exit_ticket && lesson.exit_ticket.length > 0 && (
          <div className="border-t border-border pt-4">
            <h3 className="text-sm font-medium text-foreground mb-2">Exit Ticket ({lesson.exit_ticket.length} questions)</h3>
            <div className="space-y-2">
              {lesson.exit_ticket.map((q, i) => (
                <div key={i} className="p-3 bg-background-secondary rounded-lg text-sm">
                  <p className="font-medium text-foreground">Q{i+1}. {q.question_text} <span className="text-foreground-muted text-xs font-normal">({q.question_type})</span></p>
                  {q.options && q.options.length > 0 && (
                    <ul className="mt-1 space-y-0.5">
                      {q.options.map((o, j) => <li key={j} className="text-foreground-muted text-xs">{o}</li>)}
                    </ul>
                  )}
                  <p className="mt-1 text-xs text-green-400">✓ {q.correct_answer}</p>
                  {q.explanation && <p className="text-xs text-foreground-muted mt-0.5">{q.explanation}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {lesson.differentiation && lesson.differentiation.length > 0 && (
          <div className="border-t border-border pt-4">
            <h3 className="text-sm font-medium text-foreground mb-2">Differentiated Activities</h3>
            <div className="grid grid-cols-3 gap-3">
              {lesson.differentiation.map((d, i) => (
                <div key={i} className={`p-3 rounded-lg text-sm ${
                  d.group === 'support' ? 'bg-blue-500/10 border border-blue-500/20' :
                  d.group === 'advanced' ? 'bg-purple-500/10 border border-purple-500/20' :
                  'bg-green-500/10 border border-green-500/20'
                }`}>
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium mb-1 ${
                    d.group === 'support' ? 'bg-blue-500/20 text-blue-400' :
                    d.group === 'advanced' ? 'bg-purple-500/20 text-purple-400' :
                    'bg-green-500/20 text-green-400'
                  }`}>{d.group}</span>
                  <p className="text-foreground text-xs">{d.description}</p>
                  <p className="text-foreground-muted text-xs mt-1">{d.duration_minutes}min</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {lesson.diagram_suggestions && lesson.diagram_suggestions.length > 0 && (
          <div className="border-t border-border pt-4">
            <h3 className="text-sm font-medium text-foreground mb-2">Diagram Suggestions</h3>
            <div className="space-y-2">
              {lesson.diagram_suggestions.map((d, i) => (
                <div key={i} className="p-3 bg-background-secondary rounded-lg text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-foreground">{d.title}</span>
                    <span className="text-foreground-muted text-xs">({d.diagram_type})</span>
                  </div>
                  <p className="text-foreground-muted text-xs mt-1">{d.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {lesson.misconception_activities && lesson.misconception_activities.length > 0 && (
          <div className="border-t border-border pt-4">
            <h3 className="text-sm font-medium text-foreground mb-2">Misconception Activities</h3>
            <div className="space-y-2">
              {lesson.misconception_activities.map((a, i) => (
                <div key={i} className="p-3 bg-red-500/5 border border-red-500/10 rounded-lg text-sm">
                  <p className="text-xs text-red-400 mb-1">Addressing: {a.misconception}</p>
                  <p className="font-medium text-foreground">{a.activity_name} <span className="text-foreground-muted text-xs font-normal">({a.activity_type} · {a.duration_minutes}min)</span></p>
                  <p className="text-foreground-muted text-xs mt-1">{a.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {lesson.classroom_context && (
          <div className="border-t border-border pt-4">
            <h3 className="text-sm font-medium text-foreground mb-2">Classroom Context</h3>
            <pre className="text-xs text-foreground-muted bg-background-secondary p-3 rounded-lg overflow-auto max-h-48">{JSON.stringify(lesson.classroom_context, null, 2)}</pre>
          </div>
        )}

        <p className="text-xs text-foreground-muted pt-4 border-t border-border">{t('details_created')} {lesson.created_at}</p>
      </div>
      {updating && <p className="text-sm text-foreground-muted mt-2"><Loader2 className="w-3 h-3 inline animate-spin" /> {t('details_updating')}</p>}
    </div>
  )
}
