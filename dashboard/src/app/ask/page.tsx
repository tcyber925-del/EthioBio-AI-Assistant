'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Send, MessageSquare, AlertTriangle, BookOpen, Loader2 } from 'lucide-react'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import ModelSelector from '@/components/ModelSelector'
import { fetchWithTimeout } from '@/lib/fetch'
import { isAuthenticated } from '@/lib/auth'

export default function AskPage() {
  const router = useRouter()
  const ta = useTranslations('ask')
  const tc = useTranslations('common')

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
  }, [router])

  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [sources, setSources] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [grade, setGrade] = useState(12)
  const [mode, setMode] = useState<'graph' | 'chat'>('graph')

  const askQuestion = async () => {
    if (!question.trim()) return
    setLoading(true)
    setError(null)
    setAnswer(null)

    try {
      const endpoint = mode === 'graph' ? '/graph/chat' : '/chat'
      const body = mode === 'graph'
        ? { question: question.trim(), grade_level: grade, model: selectedModel }
        : { user_id: '00000000-0000-0000-0000-000000000001', question: question.trim(), grade_level: grade, use_rag: true, model: selectedModel }

      const data = await fetchWithTimeout(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }, 120000)

      setAnswer(data.answer || '')
      setSelectedModel(data.model_used || '')
      setConfidence(data.confidence || 0)
      setSources(data.sources || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{ta('title')}</h1>
          <p className="text-sm text-foreground-muted mt-1">{ta('ask_subtitle')}</p>
        </div>
        <div className="flex items-center gap-3">
          <ModelSelector value={selectedModel} onChange={setSelectedModel} />
          <select value={grade} onChange={e => setGrade(Number(e.target.value))} className="px-3 py-2 border border-border rounded-lg text-sm bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
            {[7, 8, 9, 10, 11, 12].map(g => <option key={g} value={g}>{ta('grade_label')} {g}</option>)}
          </select>
          <div className="flex border border-border rounded-lg overflow-hidden">
            <button onClick={() => setMode('graph')} className={`px-3 py-2 text-xs font-medium transition-colors ${mode === 'graph' ? 'bg-primary text-white' : 'bg-card text-foreground-muted hover:text-foreground'}`}>{ta('graph_mode')}</button>
            <button onClick={() => setMode('chat')} className={`px-3 py-2 text-xs font-medium transition-colors ${mode === 'chat' ? 'bg-primary text-white' : 'bg-card text-foreground-muted hover:text-foreground'}`}>{ta('chat_mode')}</button>
          </div>
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border p-5 mb-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && askQuestion()}
            placeholder={ta('example_placeholder')}
            className="flex-1 px-4 py-3 border border-border rounded-lg text-sm bg-background text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            onClick={askQuestion}
            disabled={loading || !question.trim()}
            className="px-6 py-3 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
          >
            {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> {ta('thinking')}...</> : <><Send className="w-4 h-4" /> {ta('ask_button')}</>}
          </button>
        </div>
      </div>

      {loading && (
        <div className="bg-card rounded-xl border border-border p-8 text-center">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-border rounded w-3/4 mx-auto" />
            <div className="h-4 bg-border rounded w-1/2 mx-auto" />
            <div className="h-4 bg-border rounded w-2/3 mx-auto" />
          </div>
          <p className="text-sm text-foreground-muted mt-4">{ta('calling_model', { model: selectedModel || 'model' })}</p>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-5 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">{tc('error')}</p>
            <p className="text-sm text-red-400/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      {answer && !loading && (
        <div className="bg-card rounded-xl border border-border p-6">
          <div className="flex items-center gap-2 text-xs text-foreground-muted mb-4 pb-3 border-b border-border">
            <MessageSquare className="w-4 h-4" />
            <span className="font-mono">{selectedModel}</span>
            <span className="px-2 py-0.5 bg-green-500/10 text-green-400 rounded-full text-xs">{Math.round(confidence * 100)}% {ta('confidence')}</span>
          </div>
          <MarkdownRenderer content={answer} />
          {sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-border">
              <p className="text-xs text-foreground-muted font-medium mb-2">{ta('sources')}</p>
              <div className="flex flex-wrap gap-2">
                {sources.map((s, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-500/10 text-blue-400 rounded-full text-xs">
                    <BookOpen className="w-3 h-3" /> {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!answer && !loading && !error && (
        <div className="text-center py-16">
          <MessageSquare className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">{ta('no_questions')}</p>
          <p className="text-sm text-foreground-muted/60 mt-1">{ta('no_questions_subtitle')}</p>
        </div>
      )}
    </div>
  )
}
