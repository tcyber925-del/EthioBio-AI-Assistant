'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId } from '@/lib/auth'
import { Plus, FileText, Users, Clock, AlertCircle, RefreshCw, Calendar, ChevronRight } from 'lucide-react'
import Link from 'next/link'

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
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assignments, setAssignments] = useState<Assignment[]>([])

  const fetchAssignments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const userId = getUserId()
      const workspaces = await fetchWithAuth(`/api/v1/workspaces?user_id=${userId}`)
      if (workspaces.length === 0) {
        setAssignments([])
        return
      }
      const list = await fetchWithAuth(`/api/v1/assignments?workspace_id=${workspaces[0].id}`)
      setAssignments(list)
    } catch (err: any) {
      setError(err.message || 'Failed to load assignments')
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

  return (
    <DashboardLayout breadcrumbs={[{ label: 'Assignments', href: '/assignments' }]}>
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="verge-display text-4xl text-v2-text-primary leading-none">Assignments</h1>
            <p className="text-sm text-v2-text-secondary mt-1">Create, publish, and review student submissions.</p>
          </div>
          <Link
            href="/assignments/new"
            className="inline-flex items-center gap-1.5 px-4 h-10 rounded-xl bg-v2-accent text-v2-inverted text-sm font-semibold hover:bg-white transition-colors"
          >
            <Plus className="w-4 h-4" /> New Assignment
          </Link>
        </div>

        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div className="flex-1">{error}</div>
            <button onClick={fetchAssignments} className="p-1 hover:bg-v2-error/15 rounded-lg">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
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
                  <div className="p-3 rounded-xl bg-v2-accentMuted text-v2-accent border border-v2-accent/20 shrink-0">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-v2-text-primary truncate">{a.title}</h3>
                      <span className={`text-[10px] uppercase px-2 py-0.5 rounded-full font-semibold ${statusBadge(a.status)}`}>
                        {a.status}
                      </span>
                    </div>
                    <p className="text-xs text-v2-text-secondary mt-0.5 truncate">
                      {a.description || a.assignment_type}
                    </p>
                    {a.due_date && (
                      <p className="text-xs text-v2-text-secondary mt-1 flex items-center gap-1">
                        <Calendar className="w-3 h-3" /> Due: {new Date(a.due_date).toLocaleDateString()}
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
            <h3 className="text-lg font-bold text-v2-text-primary">No assignments yet</h3>
            <p className="text-sm text-v2-text-secondary mt-1">Create your first assignment to get started.</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
