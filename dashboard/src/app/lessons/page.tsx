'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { FileText, AlertTriangle, Plus, X, Loader2 } from 'lucide-react'
import { TableSkeleton } from '@/components/Skeleton'

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
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState<string | null>(null)

  const fetchLessons = () => {
    setLoading(true)
    fetch(`/api/admin/content/review?type=lesson&status=${filter}`)
      .then(res => res.json())
      .then(d => { setItems(d.items || []); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchLessons() }, [filter])

  const createLesson = async () => {
    if (!genTopic.trim()) return
    setGenerating(true)
    setGenMsg(null)
    try {
      const API = window.location.port === '3000' ? 'http://localhost:8000' : ''
      const res = await fetch(`${API}/lesson-plan/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grade_level: genGrade, topic: genTopic, duration_minutes: genDuration }),
      })
      if (!res.ok) {
        const body = await res.text();
        try { const e = JSON.parse(body); throw new Error(e.detail || 'Creation failed') }
        catch { throw new Error(body.slice(0, 120)) }
      }
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
          <h1 className="text-2xl font-bold text-gray-900">Lesson Plans</h1>
          <p className="text-sm text-gray-500 mt-1">Review and manage generated lesson plans</p>
        </div>
        <div className="flex gap-3">
          <select value={filter} onChange={e => setFilter(e.target.value)} className="px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
          <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
            <Plus className="w-4 h-4" /> Create
          </button>
        </div>
      </div>

      {genMsg && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${genMsg.startsWith('✅') ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {genMsg}
        </div>
      )}

      {loading ? <TableSkeleton />
      : error ? <div className="text-center py-12"><AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" /><p className="text-red-500">{error}</p></div>
      : items.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No lesson plans found</p>
          <p className="text-sm text-gray-400 mt-1">Click "Create" to generate a new lesson plan</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Topic</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Grade</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Objective</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map(l => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <Link href={`/lessons/${l.id}`} className="text-sm font-medium text-green-700 hover:underline">{l.topic}</Link>
                  </td>
                  <td className="px-5 py-3 text-sm text-gray-500">Grade {l.grade_level}</td>
                  <td className="px-5 py-3 text-sm text-gray-500 max-w-xs truncate">{l.objective}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      l.status === 'published' ? 'bg-green-100 text-green-800' :
                      l.status === 'draft' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
                    }`}>{l.status}</span>
                  </td>
                  <td className="px-5 py-3 text-sm text-gray-400">{l.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setShowModal(false)}>
          <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Create Lesson Plan</h2>
              <button onClick={() => setShowModal(false)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-gray-600 block mb-1">Grade Level</label>
                <select value={genGrade} onChange={e => setGenGrade(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg text-sm">
                  {[7, 8, 9, 10, 11, 12].map(g => <option key={g} value={g}>Grade {g}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm text-gray-600 block mb-1">Topic</label>
                <input type="text" value={genTopic} onChange={e => setGenTopic(e.target.value)} placeholder="e.g., Cell Biology, Evolution" className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div>
                <label className="text-sm text-gray-600 block mb-1">Duration (minutes)</label>
                <input type="number" min={20} max={120} value={genDuration} onChange={e => setGenDuration(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
              <button
                onClick={createLesson}
                disabled={generating || !genTopic.trim()}
                className="w-full py-3 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
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
