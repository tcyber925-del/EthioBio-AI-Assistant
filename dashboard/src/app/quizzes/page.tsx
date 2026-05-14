'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ClipboardCheck, AlertTriangle, Plus, X, Loader2 } from 'lucide-react'
import { TableSkeleton } from '@/components/Skeleton'

interface Quiz {
  id: string; title: string; grade_level: number
  topic: string; question_count: number; status: string; created_at: string
}

export default function QuizzesPage() {
  const [items, setItems] = useState<Quiz[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('draft')
  const [showModal, setShowModal] = useState(false)
  const [genGrade, setGenGrade] = useState(12)
  const [genTopic, setGenTopic] = useState('')
  const [genCount, setGenCount] = useState(5)
  const [genType, setGenType] = useState('multiple_choice')
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState<string | null>(null)

  const fetchQuizzes = () => {
    setLoading(true)
    fetch(`/api/admin/content/review?type=quiz&status=${filter}`)
      .then(res => res.json())
      .then(d => { setItems(d.items || []); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchQuizzes() }, [filter])

  const generateQuiz = async () => {
    if (!genTopic.trim()) return
    setGenerating(true)
    setGenMsg(null)
    try {
      const types = genType === 'mixed' ? ['multiple_choice', 'true_false'] : [genType]
      const API = window.location.port === '3000' ? 'http://localhost:8000' : ''
      const res = await fetch(`${API}/quiz/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grade_level: genGrade, topic: genTopic, question_count: genCount, types }),
      })
      if (!res.ok) {
        const body = await res.text();
        try { const e = JSON.parse(body); throw new Error(e.detail || 'Generation failed') }
        catch { throw new Error(body.slice(0, 120)) }
      }
      setShowModal(false)
      setGenTopic('')
      setGenMsg(`✅ Quiz generated for Grade ${genGrade} - ${genTopic}`)
      fetchQuizzes()
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
          <h1 className="text-2xl font-bold text-gray-900">Quizzes</h1>
          <p className="text-sm text-gray-500 mt-1">Review and manage generated quizzes</p>
        </div>
        <div className="flex gap-3">
          <select value={filter} onChange={e => setFilter(e.target.value)} className="px-3 py-2 border rounded-lg text-sm bg-white">
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
          <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
            <Plus className="w-4 h-4" /> Generate
          </button>
        </div>
      </div>

      {genMsg && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm ${genMsg.startsWith('✅') ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {genMsg}
        </div>
      )}

      {loading ? <TableSkeleton rows={5} />
      : error ? (
        <div className="text-center py-12"><AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" /><p className="text-red-500">{error}</p></div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border">
          <ClipboardCheck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">No quizzes found</p>
          <p className="text-sm text-gray-400 mt-1">Click "Generate" to create a new quiz</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Grade</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Topic</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Questions</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map(q => (
                <tr key={q.id} className="hover:bg-gray-50">
                  <td className="px-5 py-3">
                    <Link href={`/quizzes/${q.id}`} className="text-sm font-medium text-green-700 hover:underline">{q.title}</Link>
                  </td>
                  <td className="px-5 py-3 text-sm text-gray-500">Grade {q.grade_level}</td>
                  <td className="px-5 py-3 text-sm text-gray-500">{q.topic}</td>
                  <td className="px-5 py-3 text-sm text-gray-500">{q.question_count}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      q.status === 'published' ? 'bg-green-100 text-green-800' :
                      q.status === 'draft' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
                    }`}>{q.status}</span>
                  </td>
                  <td className="px-5 py-3 text-sm text-gray-400">{q.created_at?.slice(0, 10)}</td>
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
              <h2 className="text-lg font-semibold text-gray-900">Generate Quiz</h2>
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
                <input type="text" value={genTopic} onChange={e => setGenTopic(e.target.value)} placeholder="e.g., Cell Biology, Genetics" className="w-full px-3 py-2 border rounded-lg text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm text-gray-600 block mb-1">Questions</label>
                  <input type="number" min={1} max={30} value={genCount} onChange={e => setGenCount(Number(e.target.value))} className="w-full px-3 py-2 border rounded-lg text-sm" />
                </div>
                <div>
                  <label className="text-sm text-gray-600 block mb-1">Type</label>
                  <select value={genType} onChange={e => setGenType(e.target.value)} className="w-full px-3 py-2 border rounded-lg text-sm">
                    <option value="multiple_choice">Multiple Choice</option>
                    <option value="true_false">True/False</option>
                    <option value="mixed">Mixed</option>
                  </select>
                </div>
              </div>
              <button
                onClick={generateQuiz}
                disabled={generating || !genTopic.trim()}
                className="w-full py-3 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {generating ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</> : 'Generate Quiz'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
