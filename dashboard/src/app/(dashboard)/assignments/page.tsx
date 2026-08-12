'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId } from '@/lib/auth'
import { Plus, FileText, Users, Clock, Calendar, ChevronRight } from 'lucide-react'
import Link from 'next/link'
import { ErrorAlert } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

interface Assignment {
  id: string
  title: string
  description: string | null
  assignment_type: string
  status: string
  due_date: string | null
  created_at: string
}

export default function AssignmentsPage() {
  const t = useTranslations('assignments')
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)
  const [assignments, setAssignments] = useState<Assignment[]>([])

  const fetchAssignments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const userId = getUserId()
      const wsResponse = await fetchWithAuth(`/api/v1/workspaces?user_id=${userId}`)
      const workspaces = await wsResponse.json()
      if (workspaces.length === 0) {
        setAssignments([])
        return
      }
      const listResponse = await fetchWithAuth(`/api/v1/assignments?workspace_id=${workspaces[0].id}`)
      const list = await listResponse.json()
      setAssignments(list)
    } catch (err: any) {
      setError(normalizeException(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAssignments() }, [fetchAssignments])

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      draft: 'bg-v2-warning/10 text-v2-warning',
      published: 'bg-v2-success/10 text-v2-success',
      completed: 'bg-v2-accent/10 text-v2-accent',
      archived: 'bg-v2-text-secondary/10 text-v2-text-secondary',
    }
    return styles[status] || 'bg-v2-bg/40 text-v2-text-secondary'
  }
  const statusLabel = (status: string) =>
    ['draft','published','completed','archived','submitted','under_review','reviewed','revision_requested'].includes(status)
      ? t(`status_${status}` as const)
      : status

  return (
    <DashboardLayout breadcrumbs={[{ label: t('crumb'), href: '/assignments' }]}>
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="verge-display text-4xl text-v2-text-primary leading-none">{t('list_title')}</h1>
            <p className="text-sm text-v2-text-secondary mt-1">{t('list_subtitle')}</p>
          </div>
          <Link
            href="/assignments/new"
            className="inline-flex items-center gap-1.5 px-4 h-10 rounded-xl bg-v2-accent text-v2-inverted text-sm font-semibold hover:bg-white transition-colors"
          >
            <Plus className="w-4 h-4" /> {t('new_assignment')}
          </Link>
        </div>

        {error && (
          <ErrorAlert
            error={error}
            title={t('error_load')}
            onRetry={() => void fetchAssignments()}
            retrying={loading}
          />
        )}

        {loading ? (
          <div className="py-20 flex justify-center">
            <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" />
          </div>
        ) : assignments.length > 0 ? (
          <div className="flex flex-col gap-4">
            {assignments.map(a => (
              <Link
                key={a.id}
                href={`/assignments/${a.id}`}
                className="bg-v2-surface border border-v2-border rounded-[20px] p-5 flex items-center justify-between hover:border-v2-accent transition-colors group"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="p-3 rounded-xl bg-v2-accent-muted text-v2-accent border border-v2-accent/20 shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-v2-text-primary truncate">{a.title}</h3>
                      <span className={`text-[10px] uppercase px-2 py-0.5 rounded-full font-semibold ${statusBadge(a.status)}`}>
                        {statusLabel(a.status)}
                      </span>
                    </div>
                    <p className="text-xs text-v2-text-secondary mt-0.5 truncate">
                      {a.description || a.assignment_type}
                    </p>
                    {a.due_date && (
                      <p className="text-xs text-v2-text-secondary mt-1 flex items-center gap-1">
                        <Calendar className="w-3 h-3" /> {t('due_prefix', { date: new Date(a.due_date).toLocaleDateString() })}
                      </p>
                    )}
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-v2-text-secondary group-hover:text-v2-accent transition-colors shrink-0" />
              </Link>
            ))}
          </div>
        ) : (
          <div className="bg-v2-surface border border-v2-border rounded-[20px] py-16 text-center">
            <FileText className="w-12 h-12 text-v2-text-secondary mx-auto mb-3" />
            <h3 className="text-lg font-bold text-v2-text-primary">{t('empty_title')}</h3>
            <p className="text-sm text-v2-text-secondary mt-1">{t('empty_hint')}</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
