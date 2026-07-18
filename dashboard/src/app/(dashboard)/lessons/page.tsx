'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { FileText, AlertTriangle, Plus, X, Loader2, CheckCircle, XCircle, Sparkles } from 'lucide-react'
import { TableSkeleton } from '@/components/Skeleton'
import ModelSelector from '@/components/ModelSelector'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId, isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface Lesson {
  id: string; topic: string; grade_level: number
  objective: string; status: string; created_at: string
}

interface Classroom {
  id: string
  name: string
  grade_level: number
}

export default function LessonsPage() {
  const router = useRouter()
  const [items, setItems] = useState<Lesson[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('draft')
  const [showModal, setShowModal] = useState(false)
  const [genGrade, setGenGrade] = useState(12)
  const [genTopic, setGenTopic] = useState('')
  const [genDuration, setGenDuration] = useState(40)
  const [selectedModel, setSelectedModel] = useState('')
  const [classrooms, setClassrooms] = useState<Classroom[]>([])
  const [selectedClassroomId, setSelectedClassroomId] = useState('')
  const [genExitTicket, setGenExitTicket] = useState(false)
  const [genDifferentiation, setGenDifferentiation] = useState(false)
  const [genDiagrams, setGenDiagrams] = useState(false)
  const [genMisconceptions, setGenMisconceptions] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState<string | null>(null)
  const [genStatus, setGenStatus] = useState<'success' | 'error' | null>(null)
  const [genResult, setGenResult] = useState<any>(null)
  const t = useTranslations('lesson')


  const fetchLessons = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithAuth(`/api/lesson-plan?teacher_id=${getUserId()}`)
      setItems(Array.isArray(data) ? data : data.items || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchClassrooms = async () => {
    try {
      const data = await fetchWithAuth('/api/teacher/classrooms')
      setClassrooms(data || [])
    } catch (err) {
      console.error('Failed to fetch classrooms', err)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchLessons()
  }, [filter, router])

  useEffect(() => {
    if (!isAuthenticated()) return
    fetchClassrooms()
  }, [router])

  const createLesson = async () => {
    if (!genTopic.trim()) return
    setGenerating(true)
    setGenMsg(null)
    try {
      const data = await fetchWithAuth(`/lesson-plan/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          teacher_id: getUserId(),
          grade_level: genGrade,
          topic: genTopic,
          duration_minutes: genDuration,
          model: selectedModel,
          generate_exit_ticket: genExitTicket,
          generate_differentiation: genDifferentiation,
          generate_diagram_suggestions: genDiagrams,
          generate_misconception_activities: genMisconceptions,
          classroom_id: selectedClassroomId || null,
        }),
      }, 120000)
      setShowModal(false)
      setGenTopic('')
      setGenMsg(`Lesson plan created for Grade ${genGrade} - ${genTopic}`)
      setGenStatus('success')
      setGenResult(data)
      fetchLessons()
    } catch (err: any) {
      setGenMsg(err.message)
      setGenStatus('error')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('title')}</h1>
          <p className="text-sm text-foreground-muted mt-1">{t('subtitle')}</p>
        </div>
        <div className="flex gap-3">
          <select value={filter} onChange={e => setFilter(e.target.value)} className="px-3 py-2 border border-border rounded-lg text-sm bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="draft">{t('filter_draft')}</option>
            <option value="published">{t('filter_published')}</option>
            <option value="archived">{t('filter_archived')}</option>
          </select>
          <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
            <Plus className="w-4 h-4" /> {t('create')}
          </button>
        </div>
      </div>

      {genMsg && genStatus && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm flex items-center justify-between ${genStatus === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
          <span className="flex items-center gap-2">
            {genStatus === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            {genMsg}
          </span>
          <div className="flex items-center gap-2">
            {genResult && (
              <button onClick={() => setGenResult(null)} className="text-xs underline hover:no-underline">Hide details</button>
            )}
            <button onClick={() => { setGenMsg(null); setGenStatus(null); setGenResult(null); }} className="ml-3 hover:opacity-70"><X className="w-4 h-4" /></button>
          </div>
        </div>
      )}
      {genResult && (
        <div className="mb-4 bg-card border border-border rounded-xl p-4 space-y-3">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" /> Generated Content
          </h3>
          {genResult.exit_ticket && genResult.exit_ticket.length > 0 && (
            <div>
              <p className="text-xs font-medium text-foreground-muted uppercase mb-1">Exit Ticket ({genResult.exit_ticket.length} questions)</p>
              <div className="space-y-1">
                {genResult.exit_ticket.map((q: any, i: number) => (
                  <p key={i} className="text-xs text-foreground">• {q.question_text} <span className="text-foreground-muted">({q.question_type})</span></p>
                ))}
              </div>
            </div>
          )}
          {genResult.differentiation && genResult.differentiation.length > 0 && (
            <div>
              <p className="text-xs font-medium text-foreground-muted uppercase mb-1">Differentiation</p>
              <div className="space-y-1">
                {genResult.differentiation.map((d: any, i: number) => (
                  <p key={i} className="text-xs text-foreground">• {d.group}: {d.description} <span className="text-foreground-muted">({d.duration_minutes}min)</span></p>
                ))}
              </div>
            </div>
          )}
          {genResult.diagram_suggestions && genResult.diagram_suggestions.length > 0 && (
            <div>
              <p className="text-xs font-medium text-foreground-muted uppercase mb-1">Diagram Suggestions</p>
              <div className="space-y-1">
                {genResult.diagram_suggestions.map((d: any, i: number) => (
                  <p key={i} className="text-xs text-foreground">• {d.title} <span className="text-foreground-muted">({d.diagram_type})</span></p>
                ))}
              </div>
            </div>
          )}
          {genResult.misconception_activities && genResult.misconception_activities.length > 0 && (
            <div>
              <p className="text-xs font-medium text-foreground-muted uppercase mb-1">Misconception Activities</p>
              <div className="space-y-1">
                {genResult.misconception_activities.map((a: any, i: number) => (
                  <p key={i} className="text-xs text-foreground">• {a.activity_name} <span className="text-foreground-muted">({a.activity_type})</span></p>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {loading ? <TableSkeleton rows={5} />
      : error ? (
        <div className="text-center py-12"><AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" /><p className="text-red-400">{error}</p></div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-card rounded-xl border border-border">
          <FileText className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">{t('no_lessons')}</p>
          <p className="text-sm text-foreground-muted/60 mt-1">{t('create_hint')}</p>
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <table className="w-full">
            <thead className="bg-background-secondary">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_topic')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_grade')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_objective')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_status')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_created')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map(l => (
                <tr key={l.id} className="hover:bg-background-secondary/50">
                  <td className="px-5 py-3">
                    <Link href={`/lessons/${l.id}`} className="text-sm font-medium text-primary hover:underline">{l.topic}</Link>
                  </td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{t('col_grade')} {l.grade_level}</td>
                  <td className="px-5 py-3 text-sm text-foreground-muted max-w-xs truncate">{l.objective}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      l.status === 'published' ? 'bg-green-500/10 text-green-400' :
                      l.status === 'draft' ? 'bg-yellow-500/10 text-yellow-400' : 'bg-border/50 text-foreground-muted'
                    }`}>{l.status}</span>
                  </td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{l.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-start justify-center z-50 pt-[5vh]" onClick={() => setShowModal(false)}>
          <div className="bg-card border border-border rounded-xl shadow-xl p-6 w-full max-w-md mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-foreground">{t('create_title')}</h2>
              <button onClick={() => setShowModal(false)} className="text-foreground-muted hover:text-foreground transition-colors"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('grade_level')}</label>
                <select value={genGrade} onChange={e => setGenGrade(Number(e.target.value))} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                  {[7, 8, 9, 10, 11, 12].map(g => <option key={g} value={g}>{t('col_grade')} {g}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('classroom_context')}</label>
                <select value={selectedClassroomId} onChange={e => setSelectedClassroomId(e.target.value)} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                  <option value="">{t('classroom_reference_only')}</option>
                  {classrooms.map(c => <option key={c.id} value={c.id}>{c.name} (Grade {c.grade_level})</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('model')}</label>
                <ModelSelector value={selectedModel} onChange={setSelectedModel} />
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('col_topic')}</label>
                <input type="text" value={genTopic} onChange={e => setGenTopic(e.target.value)} placeholder="e.g., Cell Biology, Evolution" className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('duration_minutes')}</label>
                <input type="number" min={20} max={120} value={genDuration} onChange={e => setGenDuration(Number(e.target.value))} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>

              <div className="border-t border-border pt-3">
                <p className="text-xs font-medium text-foreground-muted mb-2 uppercase tracking-wide">Enhancements</p>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={genExitTicket} onChange={e => setGenExitTicket(e.target.checked)}
                      className="w-4 h-4 rounded border-border bg-background-secondary accent-primary" />
                    <span className="text-sm text-foreground">{t('exit_ticket')}</span>
                    <span className="text-xs text-foreground-muted">{t('exit_ticket_hint')}</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={genDifferentiation} onChange={e => setGenDifferentiation(e.target.checked)}
                      className="w-4 h-4 rounded border-border bg-background-secondary accent-primary" />
                    <span className="text-sm text-foreground">{t('differentiation')}</span>
                    <span className="text-xs text-foreground-muted">{t('differentiation_hint')}</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={genDiagrams} onChange={e => setGenDiagrams(e.target.checked)}
                      className="w-4 h-4 rounded border-border bg-background-secondary accent-primary" />
                    <span className="text-sm text-foreground">{t('diagram_suggestions')}</span>
                    <span className="text-xs text-foreground-muted">{t('diagram_suggestions_hint')}</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={genMisconceptions} onChange={e => setGenMisconceptions(e.target.checked)}
                      className="w-4 h-4 rounded border-border bg-background-secondary accent-primary" />
                    <span className="text-sm text-foreground">{t('misconception_activities')}</span>
                    <span className="text-xs text-foreground-muted">{t('misconception_activities_hint')}</span>
                  </label>
                </div>
              </div>
              <button
                onClick={createLesson}
                disabled={generating || !genTopic.trim()}
                className="w-full py-3 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
              >
                {generating ? <><Loader2 className="w-4 h-4 animate-spin" /> {t('generating')}</> : t('create_title')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
