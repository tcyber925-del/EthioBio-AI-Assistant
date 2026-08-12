'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId } from '@/lib/auth'
import { ArrowRight, CheckCircle, X } from 'lucide-react'
import { ErrorAlert } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

const ASSIGNMENT_TYPES = ['homework', 'quiz', 'project', 'lab', 'essay', 'worksheet', 'presentation']

export default function NewAssignmentPage() {
  const t = useTranslations('assignments')
  const router = useRouter()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [instructions, setInstructions] = useState('')
  const [assignmentType, setAssignmentType] = useState('homework')
  const [dueDate, setDueDate] = useState('')
  const [maxAttempts, setMaxAttempts] = useState(1)
  const [allowLate, setAllowLate] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<AppError | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const userId = getUserId()
      const wsResponse = await fetchWithAuth(`/api/v1/workspaces?user_id=${userId}`)
      const workspaces = await wsResponse.json()
      if (workspaces.length === 0) throw { category: 'client', retryable: false, params: {} } as AppError

      await fetchWithAuth(`/api/v1/assignments?teacher_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: workspaces[0].id,
          title,
          description: description || null,
          instructions: instructions || null,
          assignment_type: assignmentType,
          due_date: dueDate ? new Date(dueDate).toISOString() : null,
          max_attempts: maxAttempts,
          allow_late_submission: allowLate,
        }),
      })
      setSuccess(true)
      setTimeout(() => router.push('/assignments'), 1500)
    } catch (err: any) {
      setError(normalizeException(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <DashboardLayout breadcrumbs={[{ label: t('crumb'), href: '/assignments' }, { label: t('crumb_new') }]}>
      <div className="flex flex-col gap-6 max-w-2xl mx-auto">
        <div>
          <h1 className="verge-display text-4xl text-v2-text-primary leading-none">{t('create_title')}</h1>
          <p className="text-sm text-v2-text-secondary mt-1">{t('create_subtitle')}</p>
        </div>

        {error && (
          <ErrorAlert error={error} title={t('error_create')} />
        )}
        {success && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-success/10 border border-v2-success/30 text-v2-success text-sm">
            <CheckCircle className="w-5 h-5 shrink-0" /> {t('created_success')}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <label className="text-xs text-v2-text-secondary uppercase font-semibold">{t('field_title')}</label>
              <input type="text" value={title} onChange={e => setTitle(e.target.value)} required placeholder={t('title_placeholder')}
                className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent" />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs text-v2-text-secondary uppercase font-semibold">{t('field_description')}</label>
              <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2} placeholder={t('desc_placeholder')}
                className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent resize-none" />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs text-v2-text-secondary uppercase font-semibold">{t('field_instructions')}</label>
              <textarea value={instructions} onChange={e => setInstructions(e.target.value)} rows={4} placeholder={t('instructions_placeholder')}
                className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent resize-none" />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">{t('field_type')}</label>
                <select value={assignmentType} onChange={e => setAssignmentType(e.target.value)}
                  className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent">
                  {ASSIGNMENT_TYPES.map(at => <option key={at} value={at}>{t(`type_${at}` as const)}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">{t('field_due_date')}</label>
                <input type="datetime-local" value={dueDate} onChange={e => setDueDate(e.target.value)}
                  className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent" />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">{t('field_max_attempts')}</label>
                <input type="number" min={1} max={10} value={maxAttempts} onChange={e => setMaxAttempts(parseInt(e.target.value) || 1)}
                  className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent" />
              </div>
              <div className="flex items-end pb-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input type="checkbox" checked={allowLate} onChange={e => setAllowLate(e.target.checked)}
                    className="w-4 h-4 rounded border-v2-border text-v2-accent focus:ring-v2-accent" />
                  <span className="text-sm text-v2-text-primary font-medium">{t('allow_late')}</span>
                </label>
              </div>
            </div>
          </div>

          <button type="submit" disabled={submitting || success || !title.trim()}
            className="w-full h-12 rounded-xl bg-v2-accent text-v2-inverted text-sm font-bold hover:bg-white transition-all flex items-center justify-center gap-2 disabled:opacity-50">
            {submitting ? t('creating') : <>{t('create_submit')} <ArrowRight className="w-4 h-4" /></>}
          </button>
        </form>
      </div>
    </DashboardLayout>
  )
}
