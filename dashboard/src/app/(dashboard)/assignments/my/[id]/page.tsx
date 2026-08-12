'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId } from '@/lib/auth'
import { FileText, Calendar, AlertCircle, CheckCircle, Upload, ArrowRight, Loader, ArrowUpCircle } from 'lucide-react'
import { ErrorAlert } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

export default function StudentAssignmentDetailPage() {
  const t = useTranslations('assignments')
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const userId = getUserId()

  const [assignment, setAssignment] = useState<any>(null)
  const [mySubmissions, setMySubmissions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)

  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    const fetch = async () => {
      try {
        const [a, subs] = await Promise.all([
          fetchWithAuth(`/api/v1/assignments/${id}`).then(r => r.json()),
          fetchWithAuth(`/api/v1/assignments/submissions/my?student_id=${userId}`).then(r => r.json()),
        ])
        setAssignment(a)
        setMySubmissions(subs.filter((s: any) => s.assignment_id === id))
      } catch (err: any) {
        setError(normalizeException(err))
      } finally { setLoading(false) }
    }
    fetch()
  }, [id, userId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!content.trim()) return
    setSubmitting(true); setError(null)
    try {
      await fetchWithAuth(`/api/v1/assignments/${id}/submissions?student_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content_text: content }),
      })
      setSuccess(true)
      setContent('')
      setTimeout(() => { window.location.reload() }, 1000)
    } catch (err: any) {
      setError(normalizeException(err))
    } finally { setSubmitting(false) }
  }

  const statusBadge = (s: string) => {
    const m: Record<string, string> = {
      submitted: 'bg-v2-warning/10 text-v2-warning',
      under_review: 'bg-v2-accent/10 text-v2-accent',
      reviewed: 'bg-v2-success/10 text-v2-success',
      completed: 'bg-v2-accent/10 text-v2-accent',
      revision_requested: 'bg-v2-error/10 text-v2-error',
    }
    return m[s] || 'bg-v2-bg/40 text-v2-text-secondary'
  }
  const statusLabel = (status: string) =>
    ['draft','published','completed','archived','submitted','under_review','reviewed','revision_requested'].includes(status)
      ? t(`status_${status}` as const)
      : status

  if (loading) return <DashboardLayout breadcrumbs={[{ label: t('crumb_my'), href: '/assignments/my' }]}>
    <div className="py-20 flex justify-center"><div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" /></div></DashboardLayout>

  if (error || !assignment) return <DashboardLayout breadcrumbs={[{ label: 'My Assignments', href: '/assignments/my' }]}>
    {error ? (
      <ErrorAlert error={error} />
    ) : (
      <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
        <AlertCircle className="w-5 h-5" />{t('not_found')}</div>
    )}</DashboardLayout>

  const canSubmit = mySubmissions.length < assignment.max_attempts

  return (
    <DashboardLayout breadcrumbs={[{ label: t('crumb_my'), href: '/assignments/my' }, { label: assignment.title }]}>
      <div className="flex flex-col gap-6 max-w-2xl mx-auto">
        <div>
          <h1 className="verge-display text-4xl text-v2-text-primary leading-none">{assignment.title}</h1>
          <p className="text-sm text-v2-text-secondary mt-1">{assignment.description}</p>
        </div>

        <div className="bg-v2-surface border border-v2-border rounded-[20px] p-5 flex flex-col gap-4">
          <h2 className="text-xs text-v2-text-secondary uppercase font-semibold">{t('details')}</h2>
          <div className="flex items-center gap-3 text-sm text-v2-text-primary">
            <FileText className="w-4 h-4 text-v2-text-secondary" /> {t('type_label', { type: assignment.assignment_type })}
          </div>
          <div className="flex items-center gap-3 text-sm text-v2-text-primary">
            <Calendar className="w-4 h-4 text-v2-text-secondary" />
            {assignment.due_date ? new Date(assignment.due_date).toLocaleString() : t('no_due_date')}
          </div>
          <div className="flex items-center gap-3 text-sm text-v2-text-primary">
            <ArrowUpCircle className="w-4 h-4 text-v2-text-secondary" />
            {t('submissions_label', { used: mySubmissions.length, max: assignment.max_attempts })}
          </div>
        </div>

        {assignment.instructions && (
          <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6">
            <h2 className="text-sm font-bold text-v2-text-primary mb-3">{t('field_instructions')}</h2>
            <p className="text-sm text-v2-text-secondary whitespace-pre-wrap">{assignment.instructions}</p>
          </div>
        )}

        {mySubmissions.length > 0 && (
          <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4">
            <h2 className="text-sm font-bold text-v2-text-primary">{t('my_submissions')}</h2>
            {mySubmissions.map(s => (
              <div key={s.id} className="flex items-center justify-between p-4 bg-v2-bg/40 border border-v2-border/40 rounded-xl">
                <div>
                  <p className="text-sm text-v2-text-primary">{t('attempt_label', { n: s.attempt_number })}</p>
                  <p className="text-xs text-v2-text-secondary">{new Date(s.submitted_at).toLocaleString()}</p>
                  {s.grade !== null && <p className="text-sm font-bold text-v2-success mt-1">{t('grade_label', { grade: s.grade })}</p>}
                  {s.teacher_feedback?.comment && (
                    <p className="text-xs text-v2-text-secondary mt-1 italic">{t('feedback_prefix', { comment: s.teacher_feedback.comment })}</p>
                  )}
                </div>
                <span className={`text-[10px] uppercase px-2 py-0.5 rounded-full font-semibold ${statusBadge(s.status)}`}>
                  {statusLabel(s.status)}
                </span>
              </div>
            ))}
          </div>
        )}

        {canSubmit && (
          <form onSubmit={handleSubmit} className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-5">
            <h2 className="text-sm font-bold text-v2-text-primary">{t('submit_work')}</h2>
            <div className="flex flex-col gap-2">
              <label className="text-xs text-v2-text-secondary uppercase font-semibold">{t('your_answer')}</label>
              <textarea value={content} onChange={e => setContent(e.target.value)} rows={6} required placeholder={t('answer_placeholder')}
                className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent resize-none" />
            </div>
            {success && <p className="text-xs text-v2-success flex items-center gap-1"><CheckCircle className="w-3 h-3" /> {t('submitted_success')}</p>}
            <button type="submit" disabled={submitting || success || !content.trim()}
              className="h-12 rounded-xl bg-v2-accent text-v2-inverted text-sm font-bold hover:bg-white disabled:opacity-50 transition-all flex items-center justify-center gap-2">
              {submitting ? <><Loader className="w-4 h-4 animate-spin" /> {t('submitting')}</> : <><Upload className="w-4 h-4" /> {t('submit_action')} <ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>
        )}

        {!canSubmit && (
          <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6 text-center">
            <CheckCircle className="w-8 h-8 text-v2-text-secondary mx-auto mb-2" />
            <p className="text-sm text-v2-text-primary font-semibold">{t('max_attempts_title')}</p>
            <p className="text-xs text-v2-text-secondary mt-1">{t('max_attempts_hint', { count: assignment.max_attempts })}</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
