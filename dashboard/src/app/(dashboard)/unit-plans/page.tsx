'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { FileText, Plus, X, Loader2, CheckCircle, Sparkles } from 'lucide-react'
import { TableSkeleton } from '@/components/Skeleton'
import ModelSelector from '@/components/ModelSelector'
import { ErrorAlert, ErrorState } from '@/components/ui/errors'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'
import { normalizeException, type AppError } from '@/lib/errors'
import { useSubjectGrade } from '@/context/SubjectGradeContext'

export const dynamic = 'force-dynamic'

interface UnitPlan {
  id: string; unit_title: string; topic: string
  grade_level: number; days: number; created_at: string
}

interface Classroom {
  id: string
  name: string
  grade_level: number
}

export default function UnitPlansPage() {
  const router = useRouter()
  const [items, setItems] = useState<UnitPlan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [genTitle, setGenTitle] = useState('')
  const { grade: genGrade, subject, setGrade: setGenGrade } = useSubjectGrade()
  const [genTopic, setGenTopic] = useState('')
  const [genDays, setGenDays] = useState(5)
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
  const [genError, setGenError] = useState<AppError | null>(null)
  const [genStatus, setGenStatus] = useState<'success' | null>(null)
  const [genResult, setGenResult] = useState<any>(null)
  const t = useTranslations('unit_plans')

  const fetchPlans = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchWithAuth(`/api/lesson-plan/unit/list`)
      const data = await response.json()
      setItems(data.items || [])
    } catch (err) {
      setError(normalizeException(err))
    } finally {
      setLoading(false)
    }
  }

  const fetchClassrooms = async () => {
    try {
      const classResponse = await fetchWithAuth('/api/teacher/classrooms')
      const data = await classResponse.json()
      setClassrooms(data || [])
    } catch (err) {
      console.error('Failed to fetch classrooms', err)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchPlans()
    fetchClassrooms()
  }, [router])

  const createUnitPlan = async () => {
    if (!genTitle.trim() || !genTopic.trim()) return
    setGenerating(true)
    setGenMsg(null)
    setGenError(null)
    try {
      const genResponse = await fetchWithAuth(`/lesson-plan/unit/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          unit_title: genTitle,
          grade_level: genGrade,
          topic: genTopic,
          subject,
          days: genDays,
          duration_minutes: genDuration,
          model: selectedModel,
          generate_exit_ticket: genExitTicket,
          generate_differentiation: genDifferentiation,
          generate_diagram_suggestions: genDiagrams,
          generate_misconception_activities: genMisconceptions,
          classroom_id: selectedClassroomId || null,
        }),
      })
      const data = await genResponse.json()
      setShowModal(false)
      setGenTitle('')
      setGenTopic('')
      setGenMsg(`Unit plan "${genTitle}" created (${genDays} days)`)
      setGenStatus('success')
      setGenResult(data)
      fetchPlans()
    } catch (err) {
      setGenError(normalizeException(err))
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
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
          <Plus className="w-4 h-4" /> {t('create')}
        </button>
      </div>

      {genMsg && genStatus === 'success' && (
        <div className="mb-4 px-4 py-3 rounded-lg text-sm flex items-center justify-between bg-green-500/10 text-green-400 border border-green-500/20">
          <span className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4" />
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
      {genError && <ErrorAlert error={genError} />}
      {genResult && (
        <div className="mb-4 bg-card border border-border rounded-xl p-4 space-y-3">
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" /> {genResult.unit_title}
          </h3>
          <p className="text-xs text-foreground-muted">{genResult.days} days · Grade {genResult.grade_level} · {genResult.topic}</p>
          {genResult.lessons && genResult.lessons.map((day: any, i: number) => (
            <div key={i} className="p-3 bg-background-secondary rounded-lg text-sm">
              <p className="font-medium text-foreground">{t('day_lesson', { day: day.day_index, subtopic: day.subtopic })}</p>
              <p className="text-xs text-foreground-muted mt-1">{day.objective}</p>
            </div>
          ))}
        </div>
      )}

      {loading ? <TableSkeleton rows={5} />
      : error ? (
        <ErrorState error={error} onRetry={() => void fetchPlans()} retrying={loading} />
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-card rounded-xl border border-border">
          <FileText className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">{t('no_plans')}</p>
          <p className="text-sm text-foreground-muted/60 mt-1">{t('create_hint')}</p>
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <table className="w-full">
            <thead className="bg-background-secondary">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_title')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_topic')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_grade')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_days')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_created')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map(p => (
                <tr key={p.id} className="hover:bg-background-secondary/50">
                  <td className="px-5 py-3">
                    <Link href={`/unit-plans/${p.id}`} className="text-sm font-medium text-primary hover:underline">{p.unit_title}</Link>
                  </td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{p.topic}</td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{p.grade_level}</td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{p.days}</td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{p.created_at?.slice(0, 10)}</td>
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
                <label className="text-sm text-foreground-muted block mb-1">{t('unit_title')}</label>
                <input type="text" value={genTitle} onChange={e => setGenTitle(e.target.value)} placeholder={t('unit_title_placeholder')} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('grade_level')}</label>
                <select value={genGrade} onChange={e => setGenGrade(Number(e.target.value))} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                  {[7, 8, 9, 10, 11, 12].map(g => <option key={g} value={g}>Grade {g}</option>)}
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
                <label className="text-sm text-foreground-muted block mb-1">{t('col_topic')}</label>
                <input type="text" value={genTopic} onChange={e => setGenTopic(e.target.value)} placeholder="e.g., Cell Biology" className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('days')}</label>
                <input type="number" min={2} max={20} value={genDays} onChange={e => setGenDays(Number(e.target.value))} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('duration_minutes')}</label>
                <input type="number" min={20} max={120} value={genDuration} onChange={e => setGenDuration(Number(e.target.value))} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('model')}</label>
                <ModelSelector value={selectedModel} onChange={setSelectedModel} />
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
                onClick={createUnitPlan}
                disabled={generating || !genTitle.trim() || !genTopic.trim()}
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
