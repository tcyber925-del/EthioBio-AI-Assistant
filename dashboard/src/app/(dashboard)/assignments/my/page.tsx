'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId } from '@/lib/auth'
import { FileText, Calendar, AlertCircle, RefreshCw, ChevronRight, CheckCircle2, Clock } from 'lucide-react'
import Link from 'next/link'

interface Assignment {
  id: string; title: string; description: string | null
  assignment_type: string; status: string; due_date: string | null
  created_at: string
}

export default function MyAssignmentsPage() {
  const t = useTranslations('assignments')
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assignments, setAssignments] = useState<Assignment[]>([])

  const fetchAssignments = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const userId = getUserId()
      const response = await fetchWithAuth(`/api/v1/assignments/my?student_id=${userId}`)
      const list = await response.json()
      setAssignments(list)
    } catch (err: any) {
      setError(err.message || t('error_load'))
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchAssignments() }, [fetchAssignments])

  const isLate = (due: string | null) => due && new Date(due) < new Date()

  return (
    <DashboardLayout breadcrumbs={[{ label: t('crumb_my'), href: '/assignments/my' }]}>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="verge-display text-4xl text-v2-text-primary leading-none">{t('my_title')}</h1>
          <p className="text-sm text-v2-text-secondary mt-1">{t('my_subtitle')}</p>
        </div>

        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
            <AlertCircle className="w-5 h-5" />{error}
            <button onClick={fetchAssignments} className="p-1 hover:bg-v2-error/15 rounded-lg"><RefreshCw className="w-4 h-4" /></button>
          </div>
        )}

        {loading ? (
          <div className="py-20 flex justify-center"><div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" /></div>
        ) : assignments.length > 0 ? (
          <div className="flex flex-col gap-4">
            {assignments.map(a => {
              const late = isLate(a.due_date)
              return (
                <Link key={a.id} href={`/assignments/my/${a.id}`}
                  className="bg-v2-surface border border-v2-border rounded-[20px] p-5 flex items-center justify-between hover:border-v2-accent transition-colors group">
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="p-3 rounded-xl bg-v2-accent-muted text-v2-accent border border-v2-accent/20 shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-v2-text-primary truncate">{a.title}</h3>
                        {late && <span className="text-[10px] uppercase px-2 py-0.5 rounded-full font-semibold bg-v2-error/10 text-v2-error">{t('late_badge')}</span>}
                      </div>
                      <p className="text-xs text-v2-text-secondary mt-0.5 truncate">{a.description || a.assignment_type}</p>
                      <div className="flex items-center gap-3 mt-1 text-xs text-v2-text-secondary">
                        {a.due_date && (
                          <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{t('due_prefix', { date: new Date(a.due_date).toLocaleDateString() })}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-v2-text-secondary group-hover:text-v2-accent transition-colors shrink-0" />
                </Link>
              )
            })}
          </div>
        ) : (
          <div className="bg-v2-surface border border-v2-border rounded-[20px] py-16 text-center">
            <CheckCircle2 className="w-12 h-12 text-v2-success mx-auto mb-3" />
            <h3 className="text-lg font-bold text-v2-text-primary">{t('caught_up_title')}</h3>
            <p className="text-sm text-v2-text-secondary mt-1">{t('caught_up_hint')}</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
