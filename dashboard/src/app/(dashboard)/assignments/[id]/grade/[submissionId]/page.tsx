'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { AlertCircle, CheckCircle } from 'lucide-react'

export default function GradeSubmissionPage() {
  const t = useTranslations('assignments')
  const { id, submissionId } = useParams<{ id: string; submissionId: string }>()
  const router = useRouter()
  const [submission, setSubmission] = useState<any>(null)
  const [grade, setGrade] = useState('')
  const [feedback, setFeedback] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    fetchWithAuth(`/api/v1/assignments/submissions/${submissionId}`)
      .then(res => res.json())
      .then(setSubmission)
      .catch(err => setError(err.message))
  }, [submissionId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true); setError(null)
    try {
      await fetchWithAuth(`/api/v1/assignments/submissions/${submissionId}/review`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          status: 'reviewed',
          grade: parseFloat(grade),
          teacher_feedback: feedback ? { comment: feedback } : {},
        }),
      })
      setSuccess(true)
      setTimeout(() => router.push(`/assignments/${id}`), 1500)
    } catch (err: any) {
      setError(err.message || t('error_submit_grade'))
    } finally { setSubmitting(false) }
  }

  return (
    <DashboardLayout breadcrumbs={[
      { label: t('crumb'), href: '/assignments' },
      { label: id, href: `/assignments/${id}` },
      { label: t('crumb_grade') },
    ]}>
      <div className="flex flex-col gap-6 max-w-2xl mx-auto">
        <div>
          <h1 className="verge-display text-4xl text-v2-text-primary leading-none">{t('grade_title')}</h1>
          <p className="text-sm text-v2-text-secondary mt-1">{t('grade_subtitle')}</p>
        </div>

        {error && <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm"><AlertCircle className="w-5 h-5" />{error}</div>}
        {success && <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-success/10 border border-v2-success/30 text-v2-success text-sm"><CheckCircle className="w-5 h-5" />{t('grade_saved')}</div>}

        {submission && (
          <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4">
            <h2 className="text-sm font-bold text-v2-text-primary">{t('student_submission')}</h2>
            {submission.content_text && (
              <div className="bg-v2-bg/40 border border-v2-border/40 rounded-xl p-4 text-sm text-v2-text-primary whitespace-pre-wrap">
                {submission.content_text}
              </div>
            )}
            <p className="text-xs text-v2-text-secondary">{t('attempt_submitted', { n: submission.attempt_number, date: new Date(submission.submitted_at).toLocaleString() })}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label className="text-xs text-v2-text-secondary uppercase font-semibold">{t('field_grade')}</label>
            <input type="number" min={0} max={100} step={0.5} value={grade} onChange={e => setGrade(e.target.value)} required
              className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent w-32" />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-xs text-v2-text-secondary uppercase font-semibold">{t('field_feedback')}</label>
            <textarea value={feedback} onChange={e => setFeedback(e.target.value)} rows={4}
              placeholder={t('feedback_placeholder')}
              className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent resize-none" />
          </div>
          <button type="submit" disabled={submitting || success}
            className="h-12 rounded-xl bg-v2-accent text-v2-inverted text-sm font-bold hover:bg-white disabled:opacity-50 transition-all">
            {submitting ? t('saving') : t('submit_grade')}
          </button>
        </form>
      </div>
    </DashboardLayout>
  )
}
