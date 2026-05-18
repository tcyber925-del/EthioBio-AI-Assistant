'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { FileText, AlertTriangle, Plus, X, Loader2 } from 'lucide-react'
import { TableSkeleton } from '@/components/Skeleton'
import ModelSelector from '@/components/ModelSelector'
import { fetchWithTimeout } from '@/lib/fetch'

interface Lesson {
  id: string; topic: string; grade_level: number
  objective: string; status: string; created_at: string
}

export default function LessonsPage() {
  const [items, setItems] = useState<Lesson[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('draft')
  const [showModal, setShowModal] = useState(false)
  const [genGrade, setGenGrade] = useState(12)
  const [genTopic, setGenTopic] = useState('')
  const [genDuration, setGenDuration] = useState(40)
  const [selectedModel, setSelectedModel] = useState('')
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState<string | null>(null)

  const fetchLessons = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithTimeout(`/api/admin/content/review?type=lesson&status=${filter}`)
      setItems(data.items || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLessons() }, [filter])

  const createLesson = async () => {
    if (!genTopic.trim()) return
    setGenerating(true)
    setGenMsg(null)
    try {
      await fetchWithTimeout(`/lesson-plan/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grade_level: genGrade, topic: genTopic, duration_minutes: genDuration, model: selectedModel }),
      }, 120000)
      setShowModal(false)
      setGenTopic('')
      setGenMsg(`✅ Lesson plan created for Grade ${genGrade} - ${genTopic}`)
      fetchLessons()
    } catch (err: any) {
      setGenMsg(`❌ ${err.message}`)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Lesson Plans</h1>
          <p className="text-sm text-foreground-muted mt-1">Review and manage generated lesson plans</p>
        </div>
        <div className="flex gap-3">
          <select value={filter} onChange={e => setFilter(e.target.value)} className="px-3 py-2 border border-border rounded-lg text-sm bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
          <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
            <Plus className="w-4 h-4" /> Create
          </button>
        </div>
      </div>

      {genMsg && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm flex items-center justify-between ${genMsg.startsWith('✅') ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
          <span>{genMsg}</span>
          <button onClick={() => setGenMsg(null)} className="ml-3 hover:opacity-70"><X className="w-4 h-4" /></button>
        </div>
      )}

      {loading ? <TableSkeleton rows={5} />
      : error ? (
        <div className="text-center py-12"><AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" /><p className="text-red-400">{error}</p></div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-card rounded-xl border border-border">
          <FileText className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">No lesson plans found</p>
          <p className="text-sm text-foreground-muted/60 mt-1">Click "Create" to generate a new lesson plan</p>
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <table className="w-full">
            <thead className="bg-background-secondary">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Topic</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Grade</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Objective</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Status</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map(l => (
                <tr key={l.id} className="hover:bg-background-secondary/50">
                  <td className="px-5 py-3">
                    <Link href={`/lessons/${l.id}`} className="text-sm font-medium text-primary hover:underline">{l.topic}</Link>
                  </td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">Grade {l.grade_level}</td>
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
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-card border border-border rounded-xl shadow-xl p-6 w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-foreground">Create Lesson Plan</h2>
              <button onClick={() => setShowModal(false)} className="text-foreground-muted hover:text-foreground transition-colors"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-foreground-muted block mb-1">Grade Level</label>
                <select value={genGrade} onChange={e => setGenGrade(Number(e.target.value))} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                  {[7, 8, 9, 10, 11, 12].map(g => <option key={g} value={g}>Grade {g}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">Model</label>
                <ModelSelector value={selectedModel} onChange={setSelectedModel} />
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">Topic</label>
                <input type="text" value={genTopic} onChange={e => setGenTopic(e.target.value)} placeholder="e.g., Cell Biology, Evolution" className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">Duration (minutes)</label>
                <input type="number" min={20} max={120} value={genDuration} onChange={e => setGenDuration(Number(e.target.value))} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <button
                onClick={createLesson}
                disabled={generating || !genTopic.trim()}
                className="w-full py-3 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
              >
                {generating ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : 'Create Lesson Plan'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
