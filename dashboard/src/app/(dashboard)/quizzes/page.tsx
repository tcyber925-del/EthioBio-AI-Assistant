'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { ClipboardCheck, AlertTriangle, Plus, X, Loader2, CheckCircle, XCircle } from 'lucide-react'
import { TableSkeleton } from '@/components/Skeleton'
import ModelSelector from '@/components/ModelSelector'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId, isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface Quiz {
  id: string; title: string; grade_level: number
  topic: string; question_count: number; status: string; created_at: string
}

export default function QuizzesPage() {
  const router = useRouter()
  const [items, setItems] = useState<Quiz[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('draft')
  const [showModal, setShowModal] = useState(false)
  const [genGrade, setGenGrade] = useState(12)
  const [genTopic, setGenTopic] = useState('')
  const [genCount, setGenCount] = useState(5)
  const [genType, setGenType] = useState('multiple_choice')
  const [selectedModel, setSelectedModel] = useState('')
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState<string | null>(null)
  const [genStatus, setGenStatus] = useState<'success' | 'error' | null>(null)
  const t = useTranslations('quiz')
  const tc = useTranslations('common')

  const fetchQuizzes = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithAuth(`/api/quiz?teacher_id=${getUserId()}`)
      setItems(data.items || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchQuizzes()
  }, [filter, router])

  const generateQuiz = async () => {
    if (!genTopic.trim()) return
    setGenerating(true)
    setGenMsg(null)
    try {
      const types = genType === 'mixed' ? ['multiple_choice', 'true_false'] : [genType]
      const data = await fetchWithAuth(`/quiz/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ teacher_id: getUserId(), grade_level: genGrade, topic: genTopic, question_count: genCount, types, model: selectedModel }),
      }, 120000)
      setShowModal(false)
      setGenTopic('')
      setGenMsg(`Quiz generated for Grade ${genGrade} - ${genTopic}`)
      setGenStatus('success')
      fetchQuizzes()
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
            <Plus className="w-4 h-4" /> {t('generate')}
          </button>
        </div>
      </div>

      {genMsg && genStatus && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm flex items-center justify-between ${genStatus === 'success' ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
          <span className="flex items-center gap-2">
            {genStatus === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            {genMsg}
          </span>
          <button onClick={() => { setGenMsg(null); setGenStatus(null); }} className="ml-3 hover:opacity-70"><X className="w-4 h-4" /></button>
        </div>
      )}

      {loading ? <TableSkeleton rows={5} />
      : error ? (
        <div className="text-center py-12"><AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" /><p className="text-red-400">{error}</p></div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-card rounded-xl border border-border">
          <ClipboardCheck className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">{t('no_quizzes')}</p>
          <p className="text-sm text-foreground-muted/60 mt-1">{t('generate_hint')}</p>
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <table className="w-full">
            <thead className="bg-background-secondary">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_title')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_grade')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_topic')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_questions')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_status')}</th>
                <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('col_created')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map(q => (
                <tr key={q.id} className="hover:bg-background-secondary/50">
                  <td className="px-5 py-3">
                    <Link href={`/quizzes/${q.id}`} className="text-sm font-medium text-primary hover:underline">{q.title}</Link>
                  </td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{t('col_grade')} {q.grade_level}</td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{q.topic}</td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{q.question_count}</td>
                  <td className="px-5 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      q.status === 'published' ? 'bg-green-500/10 text-green-400' :
                      q.status === 'draft' ? 'bg-yellow-500/10 text-yellow-400' : 'bg-border/50 text-foreground-muted'
                    }`}>{q.status}</span>
                  </td>
                  <td className="px-5 py-3 text-sm text-foreground-muted">{q.created_at?.slice(0, 10)}</td>
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
              <h2 className="text-lg font-semibold text-foreground">{t('generate_title')}</h2>
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
                <label className="text-sm text-foreground-muted block mb-1">{t('topic')}</label>
                <input type="text" value={genTopic} onChange={e => setGenTopic(e.target.value)} placeholder="e.g., Cell Biology, Genetics" className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm text-foreground-muted block mb-1">{t('model')}</label>
                  <ModelSelector value={selectedModel} onChange={setSelectedModel} />
                </div>
                <div>
                  <label className="text-sm text-foreground-muted block mb-1">{t('col_questions')}</label>
                  <input type="number" min={1} max={30} value={genCount} onChange={e => setGenCount(Number(e.target.value))} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
                </div>
              </div>
              <div>
                <label className="text-sm text-foreground-muted block mb-1">{t('type')}</label>
                <select value={genType} onChange={e => setGenType(e.target.value)} className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                  <option value="multiple_choice">{t('multiple_choice')}</option>
                  <option value="true_false">{t('true_false')}</option>
                  <option value="mixed">{t('mixed')}</option>
                </select>
              </div>
              <button
                onClick={generateQuiz}
                disabled={generating || !genTopic.trim()}
                className="w-full py-3 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
              >
                {generating ? <><Loader2 className="w-4 h-4 animate-spin" /> {t('generating')}</> : t('generate')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
