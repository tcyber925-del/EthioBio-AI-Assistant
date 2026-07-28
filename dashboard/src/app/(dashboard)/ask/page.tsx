'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import { Send, MessageSquare, AlertTriangle, BookOpen, Loader2, RefreshCw, ClipboardCheck } from 'lucide-react'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import ModelSelector from '@/components/ModelSelector'
import { DashboardLayout } from '@/components/dashboard-v2/DashboardLayout'
import { ConversationSidebar } from '@/components/ConversationSidebar'
import { useConversationHistory } from '@/hooks/useConversationHistory'
import { TTSPlayButton } from '@/components/TTSPlayButton'
import { VoiceRecorderButton } from '@/components/VoiceRecorderButton'
import { getUserId, isAuthenticated } from '@/lib/auth'
import { streamFetch } from '@/lib/fetch'

const isServerError = (msg: string) =>
  msg.includes('502') || msg.includes('504') || msg.includes('Application failed to respond')

export const dynamic = 'force-dynamic'

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
  const [statusText, setStatusText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [grade, setGrade] = useState(12)
  const [mode, setMode] = useState<'graph' | 'chat'>('graph')
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null)

  const {
    dateGroups,
    loading: loadingHistory,
    error: historyError,
    fetchHistory,
  } = useConversationHistory(50)

  const askQuestion = async () => {
    if (!question.trim()) return
    setLoading(true)
    setStatusText('Analyzing your question...')
    setError(null)
    setAnswer(null)
    setSources([])

    const endpoint = mode === 'graph' ? '/graph/chat' : '/chat'
    const body = {
      user_id: getUserId() || '00000000-0000-0000-0000-000000000001',
      question: question.trim(),
      grade_level: grade,
      model: selectedModel,
      ...(mode !== 'graph' && { use_rag: true }),
    }

    let accumulated = ''
    let gotMetadata = false

    await streamFetch(endpoint, body, {
      onStatus: (status) => {
        setStatusText(status)
      },
      onToken: (token) => {
        if (gotMetadata) return
        accumulated += token
        setAnswer(accumulated)
      },
      onMetadata: (meta) => {
        gotMetadata = true
        if (meta.model_used) setSelectedModel(meta.model_used as string)
        if (meta.confidence != null) setConfidence(meta.confidence as number)
        if (meta.sources) setSources(meta.sources as string[])
      },
      onError: (err) => {
        setError(err)
        setLoading(false)
      },
      onDone: () => {
        setStatusText(null)
        setLoading(false)
        setActiveHistoryId(null)
        fetchHistory()
      },
    })
  }

  const handleHistorySelect = (pair: { question: { content: string }, answer: { content: string } | null, id: string }) => {
    setQuestion(pair.question.content)
    setAnswer(pair.answer?.content ?? null)
    setActiveHistoryId(pair.id)
    setSelectedModel('')
    setConfidence(0)
    setSources([])
  }

  const handleVoiceTranscript = (text: string) => {
    setQuestion(text)
    setTimeout(() => {
      const btn = document.querySelector<HTMLButtonElement>('[data-ask-button]')
      btn?.click()
    }, 300)
  }

  const chatArea = (
    <div className="lg:col-span-2 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <ModelSelector value={selectedModel} onChange={setSelectedModel} />
          <select
            value={grade}
            onChange={e => setGrade(Number(e.target.value))}
            className="px-3 py-2 border border-v2-border rounded-lg text-sm bg-v2-bg text-v2-text-primary focus:outline-none focus:ring-1 focus:ring-v2-accent"
          >
            {[7, 8, 9, 10, 11, 12].map(g => (
              <option key={g} value={g}>{ta('grade_label')} {g}</option>
            ))}
          </select>
          <div className="flex border border-v2-border rounded-lg shrink-0">
            <button
              onClick={() => setMode('graph')}
              className={`px-3 py-2 text-xs font-medium transition-colors ${
                mode === 'graph' ? 'bg-v2-accent text-v2-inverted' : 'bg-v2-bg text-v2-text-muted hover:text-v2-text-primary'
              }`}
            >
              {ta('graph_mode')}
            </button>
            <button
              onClick={() => setMode('chat')}
              className={`px-3 py-2 text-xs font-medium transition-colors ${
                mode === 'chat' ? 'bg-v2-accent text-v2-inverted' : 'bg-v2-bg text-v2-text-muted hover:text-v2-text-primary'
              }`}
            >
              {ta('chat_mode')}
            </button>
          </div>
          <Link
            href="/quiz/take"
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium border border-v2-border rounded-lg text-v2-text-muted hover:text-v2-text-primary hover:border-v2-accent/50 transition-colors"
          >
            <ClipboardCheck className="w-3.5 h-3.5" />
            {ta('take_quiz')}
          </Link>
        </div>
      </div>

      <div className="rounded-[20px] border border-v2-border bg-v2-bg p-4">
        <div className="flex gap-3">
          <VoiceRecorderButton
            onTranscript={handleVoiceTranscript}
            onError={setError}
            disabled={loading}
            gradeLevel={grade}
            language="am"
          />
          <input
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && askQuestion()}
            placeholder={ta('example_placeholder')}
            className="flex-1 px-4 py-3 border border-v2-border rounded-lg text-sm bg-v2-surface text-v2-text-primary placeholder:text-v2-text-muted/50 focus:outline-none focus:ring-1 focus:ring-v2-accent"
          />
          <button
            data-ask-button
            onClick={askQuestion}
            disabled={loading || !question.trim()}
            className="px-6 py-3 bg-v2-accent text-v2-inverted rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-opacity"
          >
            {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> {ta('thinking')}...</> : <><Send className="w-4 h-4" /> {ta('ask_button')}</>}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-[20px] border border-red-500/20 bg-red-500/10 p-5 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="font-medium text-red-400">{tc('error')}</p>
            <p className="text-sm text-red-400/80 mt-1">{error}</p>
            {isServerError(error) && (
              <p className="text-xs text-red-400/60 mt-2">{ta('server_error_hint')}</p>
            )}
            <button
              onClick={askQuestion}
              disabled={loading}
              className="mt-3 px-4 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/30 transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              {tc('retry')}
            </button>
          </div>
        </div>
      )}

      {loading && !answer && (
        <div className="rounded-[20px] border border-v2-border bg-v2-bg p-8 text-center">
          <div className="flex items-center justify-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-v2-accent" />
            <p className="text-sm text-v2-text-muted">{statusText || ta('calling_model', { model: selectedModel || 'model' })}</p>
          </div>
        </div>
      )}

      {answer && (
        <div className="rounded-[20px] border border-v2-border bg-v2-bg p-6">
          {!loading && (
            <div className="flex items-center gap-2 text-xs text-v2-text-muted mb-4 pb-3 border-b border-v2-border">
              <MessageSquare className="w-4 h-4" />
              <span className="font-mono">{selectedModel}</span>
              <span className="px-2 py-0.5 bg-v2-accent/10 text-v2-accent rounded-full text-xs">
                {Math.round(confidence * 100)}% {ta('confidence')}
              </span>
            </div>
          )}
          <MarkdownRenderer content={answer} />
          {loading && (
            <div className="flex items-center gap-2 mt-4 text-xs text-v2-text-muted">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>{statusText || ta('calling_model', { model: selectedModel || 'model' })}</span>
            </div>
          )}
          {!loading && (
            <div className="mt-4 pt-3 border-t border-v2-border flex items-center gap-2">
              <TTSPlayButton text={answer} language="am" />
              <span className="text-xs text-v2-text-muted">{ta('listen')}</span>
            </div>
          )}
          {!loading && sources.length > 0 && (
            <div className="mt-4 pt-3 border-t border-v2-border">
              <p className="text-xs text-v2-text-muted font-medium mb-2">{ta('sources')}</p>
              <div className="flex flex-wrap gap-2">
                {sources.map((s, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 bg-v2-accent/10 text-v2-accent rounded-full text-xs">
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
          <MessageSquare className="w-12 h-12 text-v2-text-muted/20 mx-auto mb-3" />
          <p className="text-v2-text-muted font-medium">{ta('no_questions')}</p>
          <p className="text-sm text-v2-text-muted/60 mt-1">{ta('no_questions_subtitle')}</p>
        </div>
      )}
    </div>
  )

  return (
    <DashboardLayout breadcrumbs={[{ label: ta('title') }]}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {chatArea}
        <ConversationSidebar
          dateGroups={dateGroups}
          loading={loadingHistory}
          error={historyError}
          activeId={activeHistoryId}
          onSelect={handleHistorySelect}
          onRefresh={fetchHistory}
        />
      </div>
    </DashboardLayout>
  )
}
