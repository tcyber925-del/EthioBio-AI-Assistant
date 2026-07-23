'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId, getUserRole } from '@/lib/auth'
import {
  FileText, Users, Calendar, Clock, AlertCircle, RefreshCw, CheckCircle2,
  Download, ChevronRight, Send, ArrowUpCircle, Edit3
} from 'lucide-react'
import Link from 'next/link'

interface Assignment {
  id: string; title: string; description: string | null; instructions: string | null
  assignment_type: string; due_date: string | null; status: string
  max_attempts: number; allow_late_submission: boolean; created_at: string
}

interface Submission {
  id: string; student_id: string; storage_key: string | null
  content_text: string | null; status: string; grade: number | null
  attempt_number: number; submitted_at: string
}

export default function AssignmentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const role = getUserRole()
  const isTeacher = role === 'admin' || role === 'teacher'

  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const [a, subs] = await Promise.all([
        fetchWithAuth(`/api/v1/assignments/${id}`).then(r => r.json()),
        isTeacher ? fetchWithAuth(`/api/v1/assignments/${id}/submissions`).then(r => r.json()) : Promise.resolve([]),
      ])
      setAssignment(a); setSubmissions(subs)
    } catch (err: any) {
      setError(err.message || 'Failed to load assignment')
    } finally { setLoading(false) }
  }, [id, isTeacher])

  useEffect(() => { fetchData() }, [fetchData])

  const handlePublish = async () => {
    try {
      await fetchWithAuth(`/api/v1/assignments/${id}/publish`, { method: 'POST' })
      fetchData()
    } catch (err: any) { alert(err.message) }
  }

  const statusBadge = (s: string) => {
    const m: Record<string, string> = {
      draft: 'bg-v2-warning/10 text-v2-warning', published: 'bg-v2-success/10 text-v2-success',
      completed: 'bg-v2-accent/10 text-v2-accent', archived: 'bg-v2-text-secondary/10 text-v2-text-secondary',
    }
    return m[s] || 'bg-v2-bg/40 text-v2-text-secondary'
  }

  if (loading) return <DashboardLayout breadcrumbs={[{ label: 'Assignments', href: '/assignments' }]}>
    <div className="py-20 flex justify-center"><div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" /></div></DashboardLayout>

  if (error || !assignment) return <DashboardLayout breadcrumbs={[{ label: 'Assignments', href: '/assignments' }]}>
    <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
      <AlertCircle className="w-5 h-5" /> {error || 'Assignment not found'}</div></DashboardLayout>

  return (
    <DashboardLayout breadcrumbs={[{ label: 'Assignments', href: '/assignments' }, { label: assignment.title }]}>
      <div className="flex flex-col gap-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <h1 className="verge-display text-4xl text-v2-text-primary leading-none truncate">{assignment.title}</h1>
              <span className={`text-xs uppercase px-2 py-0.5 rounded-full font-semibold shrink-0 ${statusBadge(assignment.status)}`}>
                {assignment.status}
              </span>
            </div>
            <p className="text-sm text-v2-text-secondary mt-1">{assignment.description || assignment.assignment_type}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {assignment.status === 'draft' && (
              <button onClick={handlePublish}
                className="inline-flex items-center gap-1.5 px-4 h-10 rounded-xl bg-v2-accent text-v2-inverted text-sm font-semibold hover:bg-white transition-colors">
                <Send className="w-4 h-4" /> Publish
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 flex flex-col gap-6">
            {assignment.instructions && (
              <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6">
                <h2 className="text-sm font-bold text-v2-text-primary mb-3">Instructions</h2>
                <p className="text-sm text-v2-text-secondary whitespace-pre-wrap">{assignment.instructions}</p>
              </div>
            )}

            {isTeacher && (
              <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6">
                <h2 className="text-sm font-bold text-v2-text-primary mb-4 flex items-center gap-2">
                  <Users className="w-4 h-4" /> Submissions ({submissions.length})
                </h2>
                {submissions.length === 0 ? (
                  <p className="text-sm text-v2-text-secondary">No submissions yet.</p>
                ) : (
                  <div className="flex flex-col gap-3">
                    {submissions.map(s => (
                      <div key={s.id} className="flex items-center justify-between p-4 bg-v2-bg/40 border border-v2-border/40 rounded-xl">
                        <div>
                          <p className="text-sm font-semibold text-v2-text-primary">Student: {s.student_id.slice(0, 8)}...</p>
                          <p className="text-xs text-v2-text-secondary mt-0.5">
                            Attempt {s.attempt_number} · {new Date(s.submitted_at).toLocaleString()}
                          </p>
                          {s.status !== 'submitted' && (
                            <p className="text-xs mt-1 font-medium text-v2-success">Grade: {s.grade ?? '—'}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] uppercase px-2 py-0.5 rounded-full font-semibold ${statusBadge(s.status)}`}>
                            {s.status}
                          </span>
                          <button onClick={() => router.push(`/assignments/${id}/grade/${s.id}`)}
                            className="p-2 rounded-lg border border-v2-border hover:border-v2-accent text-v2-text-secondary hover:text-v2-accent transition-colors">
                            <Edit3 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-4">
            <div className="bg-v2-surface border border-v2-border rounded-[20px] p-5 flex flex-col gap-4">
              <h2 className="text-xs text-v2-text-secondary uppercase font-semibold">Details</h2>
              <div className="flex items-center gap-3 text-sm text-v2-text-primary">
                <FileText className="w-4 h-4 text-v2-text-secondary" /> Type: {assignment.assignment_type}
              </div>
              <div className="flex items-center gap-3 text-sm text-v2-text-primary">
                <Calendar className="w-4 h-4 text-v2-text-secondary" />
                {assignment.due_date ? new Date(assignment.due_date).toLocaleString() : 'No due date'}
              </div>
              <div className="flex items-center gap-3 text-sm text-v2-text-primary">
                <Clock className="w-4 h-4 text-v2-text-secondary" /> Max attempts: {assignment.max_attempts}
              </div>
              <div className="flex items-center gap-3 text-sm text-v2-text-primary">
                <ArrowUpCircle className="w-4 h-4 text-v2-text-secondary" />
                {assignment.allow_late_submission ? 'Late allowed' : 'No late submissions'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
