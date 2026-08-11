'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import Link from 'next/link'
import { Send, MessageSquare, AlertTriangle, BookOpen, Loader2, RefreshCw, ClipboardCheck, Mic, Square, Volume2, Plus } from 'lucide-react'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import ModelSelector from '@/components/ModelSelector'
import { CopyButton } from '@/components/CopyButton'
import { markdownToPlainText } from '@/lib/markdownToPlainText'
import { DashboardLayout } from '@/components/dashboard-v2/DashboardLayout'
import { ConversationSidebar } from '@/components/ConversationSidebar'
import { useConversationHistory } from '@/hooks/useConversationHistory'
import { TTSPlayButton } from '@/components/TTSPlayButton'
import { VoiceRecorderButton } from '@/components/VoiceRecorderButton'
import { AudioPlayer, type AudioPlayerHandle } from '@/components/AudioPlayer'
import { WaveAnimation } from '@/components/WaveAnimation'
import { getToken, getUserId, initAuth, isAuthenticated } from '@/lib/auth'
import { streamFetch } from '@/lib/fetch'
import { useVoiceTurn } from '@/hooks/useVoiceTurn'
import { isVoiceTurnEnabled } from '@/lib/voice-turn'

const isServerError = (msg: string) =>
  msg.includes('502') || msg.includes('504') || msg.includes('Application failed to respond')

export const dynamic = 'force-dynamic'

export default function AskPage() {
  const router = useRouter()
  const ta = useTranslations('ask')
  const tc = useTranslations('common')
  const tRoot = useTranslations()
  const locale = useLocale()

  useEffect(() => {
    let cancelled = false
    initAuth().then(() => {
      if (cancelled) return
      if (!isAuthenticated() || !getUserId()) router.push('/login')
    })
    return () => {
      cancelled = true
    }
  }, [router])

  const [question, setQuestion] = useState('')
  const [isListening, setIsListening] = useState(false)
  const [answer, setAnswer] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [sources, setSources] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [statusText, setStatusText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const voiceTriggeredRef = useRef(false)
  const lastAnswerRef = useRef('')
  const [grade, setGrade] = useState(12)
  const [mode, setMode] = useState<'graph' | 'chat'>('graph')
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null)
  const [voiceTurnEnabled, setVoiceTurnEnabled] = useState(false)
  const [turnAnswer, setTurnAnswer] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const turn = useVoiceTurn({
    gradeLevel: grade,
    language: locale,
    selectedModel,
    onTranscript: (text) => {
      setQuestion(text)
    },
    onToken: (token) => {
      setTurnAnswer((prev) => (prev ?? '') + token)
    },
    onError: (err) => {
      setError(err)
    },
  })

  useEffect(() => {
    isVoiceTurnEnabled().then(setVoiceTurnEnabled)
  }, [])

  const {
    dateGroups,
    loading: loadingHistory,
    error: historyError,
    fetchHistory,
  } = useConversationHistory(50)

  const askQuestion = async () => {
    if (!question.trim()) return
    const userId = getUserId()
    if (!userId) {
      setError(ta('auth_required'))
      router.push('/login')
      return
    }
    setLoading(true)
    setStatusText('Analyzing your question...')
    setError(null)
    setAnswer(null)
    setSources([])

    const endpoint = mode === 'graph' ? '/graph/chat' : '/chat'
    const body = {
      user_id: userId,
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
        lastAnswerRef.current = accumulated
        setAnswer(accumulated)
      },
      onMetadata: (meta) => {
        gotMetadata = true
        if (meta.model_used) setSelectedModel(meta.model_used as string)
        if (meta.confidence != null) setConfidence(meta.confidence as number)
        if (meta.sources) setSources(meta.sources as string[])
      },
      onError: (err) => {
        setError(tRoot(err.category === 'network' ? 'errors.categories.network' : 'errors.generic'))
        setLoading(false)
      },
      onDone: () => {
        setStatusText(null)
        setLoading(false)
        setActiveHistoryId(null)
        if (voiceTriggeredRef.current && lastAnswerRef.current) {
          voiceTriggeredRef.current = false
          playTTS(lastAnswerRef.current)
        }
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

  const handleNewChat = () => {
    setQuestion('')
    setAnswer(null)
    setTurnAnswer(null)
    setSources([])
    setConfidence(0)
    setError(null)
    setStatusText(null)
    setActiveHistoryId(null)
    turn.reset()
    inputRef.current?.focus()
  }

  const handleVoiceTranscript = (text: string) => {
    setQuestion(text)
    setIsListening(false)
    voiceTriggeredRef.current = true
    setTimeout(() => {
      const btn = document.querySelector<HTMLButtonElement>('[data-ask-button]')
      btn?.click()
    }, 300)
  }

  const handlePartialTranscript = (text: string) => {
    setQuestion(text)
    setIsListening(true)
  }

  const playTTS = async (text: string) => {
    try {
      const token = getToken()
      const res = await fetch('/chat/tts', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text, language: 'am' }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.onended = () => URL.revokeObjectURL(url)
      await audio.play()
    } catch {
      // silent fail — user can still tap the TTS button
    }
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
          <button
            onClick={handleNewChat}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-v2-accent text-v2-inverted rounded-lg hover:opacity-90 transition-opacity"
          >
            <Plus className="w-3.5 h-3.5" />
            {ta('new_chat')}
          </button>
        </div>
      </div>

      <div className="rounded-[20px] border border-v2-border bg-v2-bg p-4">
        <AudioPlayer
          ref={turn.audioPlayerRef as React.Ref<AudioPlayerHandle>}
          onStateChange={(state) => {
            if (state === 'idle' && turn.state === 'speaking') {
              turn.reset()
            }
          }}
          onError={(err) => setError(err)}
        />
        <div className="flex gap-3">
          {voiceTurnEnabled ? (
            <button
              onClick={() => {
                if (turn.state === 'idle' || turn.state === 'error') {
                  setTurnAnswer(null)
                  setError(null)
                  turn.startRecording()
                } else if (turn.state === 'recording') {
                  turn.stopRecording()
                } else if (turn.state === 'speaking') {
                  turn.stopPlayback()
                }
              }}
              disabled={turn.state === 'processing'}
              className={`w-10 h-10 shrink-0 flex items-center justify-center rounded-lg text-sm font-medium transition-all ${
                turn.state === 'recording'
                  ? 'bg-red-500 text-white animate-pulse'
                  : turn.state === 'speaking'
                    ? 'bg-green-500 text-white'
                    : turn.state === 'processing'
                      ? 'bg-v2-accent/10 text-v2-text-muted'
                      : turn.state === 'error'
                        ? 'bg-red-500/10 text-red-500'
                        : 'bg-v2-accent/10 text-v2-accent hover:bg-v2-accent/20'
              }`}
            >
              {turn.state === 'recording' ? (
                <Square className="w-4 h-4" />
              ) : turn.state === 'speaking' ? (
                <Volume2 className="w-4 h-4" />
              ) : turn.state === 'processing' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Mic className="w-4 h-4" />
              )}
            </button>
          ) : (
            <VoiceRecorderButton
              onTranscript={handleVoiceTranscript}
              onPartialTranscript={handlePartialTranscript}
              onError={setError}
              disabled={loading}
              gradeLevel={grade}
              language="am"
              streaming
            />
          )}
          <div className="relative flex-1">
            {(turn.state === 'recording' || turn.state === 'speaking') && (
              <div className="absolute inset-0 z-10 pointer-events-none">
                <WaveAnimation
                  audioLevel={turn.audioLevel}
                  source={turn.state === 'speaking' ? 'speaker' : 'mic'}
                  className="w-full h-full"
                />
              </div>
            )}
            <input
              ref={inputRef}
              type="text"
              value={question}
              onChange={e => { setQuestion(e.target.value); setIsListening(false) }}
              onKeyDown={e => e.key === 'Enter' && askQuestion()}
              placeholder={isListening || turn.state === 'recording' ? ta('listening') : ta('example_placeholder')}
              className={`flex-1 w-full px-4 py-3 border rounded-lg text-sm bg-v2-surface text-v2-text-primary focus:outline-none focus:ring-1 focus:ring-v2-accent ${
                isListening || turn.state === 'recording' ? 'border-v2-accent border-dashed' : 'border-v2-border'
              } ${turn.state === 'speaking' ? 'border-green-500/50' : ''}`}
            />
          </div>
          <button
            data-ask-button
            onClick={askQuestion}
            disabled={loading || !question.trim() || turn.state !== 'idle'}
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

      {turn.state === 'processing' && !turnAnswer && (
        <div className="rounded-[20px] border border-v2-border bg-v2-bg p-8 text-center">
          <div className="flex items-center justify-center gap-3">
            <Loader2 className="w-5 h-5 animate-spin text-v2-accent" />
            <p className="text-sm text-v2-text-muted">{ta('thinking')}</p>
          </div>
        </div>
      )}

      {(answer || turnAnswer) && (
        <div className="rounded-[20px] border border-v2-border bg-v2-bg p-6">
          {!loading && !turnAnswer && (
            <div className="flex items-center gap-2 text-xs text-v2-text-muted mb-4 pb-3 border-b border-v2-border">
              <MessageSquare className="w-4 h-4" />
              <span className="font-mono">{selectedModel}</span>
              <span className="px-2 py-0.5 bg-v2-accent/10 text-v2-accent rounded-full text-xs">
                {Math.round(confidence * 100)}% {ta('confidence')}
              </span>
            </div>
          )}
          <MarkdownRenderer content={turnAnswer || answer || ''} />
          {loading && (
            <div className="flex items-center gap-2 mt-4 text-xs text-v2-text-muted">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>{statusText || ta('calling_model', { model: selectedModel || 'model' })}</span>
            </div>
          )}
          {turn.state === 'processing' && (
            <div className="flex items-center gap-2 mt-4 text-xs text-v2-text-muted">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>{ta('thinking')}</span>
            </div>
          )}
          {!loading && !turnAnswer && (
            <div className="mt-4 pt-3 border-t border-v2-border flex items-center gap-2">
              <TTSPlayButton text={answer!} language="am" />
              <span className="text-xs text-v2-text-muted">{ta('listen')}</span>
              <CopyButton text={markdownToPlainText(answer!)} />
            </div>
          )}
          {!loading && !turnAnswer && sources.length > 0 && (
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

      {!answer && !turnAnswer && !loading && !error && turn.state === 'idle' && (
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
          onNewChat={handleNewChat}
        />
      </div>
    </DashboardLayout>
  )
}
