'use client'

import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { useRouter } from 'next/navigation'
import { DashboardLayout } from '@/components/dashboard-v2'
import ModelSelector from '@/components/ModelSelector'
import { isAuthenticated, getUserId } from '@/lib/auth'
import { streamFetch } from '@/lib/fetch'
import { normalizeException, type AppError } from '@/lib/errors'
import { ErrorAlert } from '@/components/ui/errors'
import { Bot, Send, Sparkles, User as UserIcon, FileText, ClipboardCheck } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant' | 'status'
  content: string
}

const DEFAULT_PROMPTS = [
  'Who needs attention in my class?',
  'Create a quiz on cell division for grade 10',
  'Plan a lesson about photosynthesis',
  'Summarize the state of my workspace',
]

export default function CopilotPage() {
  const t = useTranslations('copilot')
  const tn = useTranslations('v2.nav')
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<AppError | null>(null)
  const [selectedModel, setSelectedModel] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    setReady(true)
  }, [router])

  useEffect(() => {
    if (typeof endRef.current?.scrollIntoView === 'function') {
      endRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, busy])

  const send = async (text?: string) => {
    const message = (text ?? input).trim()
    if (!message || busy) return
    setInput('')
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setBusy(true)

    let accumulated = ''

    try {
      await streamFetch(
        '/copilot/query',
        { message, model: selectedModel },
        {
          onStatus: (status) => {
            setMessages((prev) => [...prev.filter((m) => m.role !== 'status'), { role: 'status', content: status }])
          },
          onToken: (token) => {
            accumulated += token
            setMessages((prev) => {
              const rest = prev.filter((m) => m.role !== 'status')
              const last = rest[rest.length - 1]
              if (last?.role === 'assistant') {
                return [...rest.slice(0, -1), { role: 'assistant', content: last.content + token }]
              }
              return [...rest, { role: 'assistant', content: token }]
            })
          },
          onError: (err) => {
            setError(err)
          },
        },
      )
    } catch (err) {
      setError(normalizeException(err))
    } finally {
      setBusy(false)
    }
  }

  if (!ready) return null

  return (
    <DashboardLayout breadcrumbs={[{ label: tn('copilot') }]}>
      <div className="flex flex-col gap-4 max-w-3xl mx-auto h-[calc(100vh-140px)]">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-v2-accent-muted text-v2-accent border border-v2-accent/30">
            <Sparkles className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="verge-display text-3xl text-v2-text-primary leading-none">{t('title')}</h1>
            <p className="text-sm text-v2-text-secondary mt-1">{t('subtitle')}</p>
          </div>
          <div className="w-52 shrink-0">
            <ModelSelector value={selectedModel} onChange={setSelectedModel} disabled={busy} />
          </div>
        </div>

        {error && (
          <ErrorAlert error={error} onRetry={error.retryable ? () => void send() : undefined} retrying={busy} />
        )}

        <div className="flex-1 overflow-y-auto rounded-[20px] bg-v2-surface/40 border border-v2-border p-4 space-y-3">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center gap-4 text-center px-4">
              <div className="p-4 rounded-full bg-v2-bg text-v2-text-secondary">
                <Bot className="w-8 h-8" />
              </div>
              <p className="text-sm text-v2-text-secondary max-w-sm">{t('empty_hint')}</p>
              <div className="flex flex-col sm:flex-row gap-2 flex-wrap justify-center">
                {DEFAULT_PROMPTS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => void send(p)}
                    disabled={busy}
                    className="text-xs text-v2-text-primary bg-v2-bg border border-v2-border rounded-xl px-3 py-2 hover:border-v2-accent transition-colors disabled:opacity-50"
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => {
            if (m.role === 'status') {
              return (
                <div key={i} className="text-xs text-v2-text-secondary italic px-2">
                  {m.content}
                </div>
              )
            }
            const isUser = m.role === 'user'
            return (
              <div key={i} className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}>
                <div
                  className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    isUser ? 'bg-v2-accent text-v2-inverted' : 'bg-v2-accent-muted text-v2-accent'
                  }`}
                >
                  {isUser ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>
                <div
                  className={`rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap max-w-[85%] ${
                    isUser
                      ? 'bg-v2-accent text-v2-inverted'
                      : 'bg-v2-bg border border-v2-border text-v2-text-primary'
                  }`}
                >
                  {m.content}
                </div>
              </div>
            )
          })}

          {busy && (
            <div className="flex items-center gap-2 text-sm text-v2-text-secondary px-2">
              <span className="w-2 h-2 rounded-full bg-v2-accent animate-pulse" />
              {t('thinking')}
            </div>
          )}
          <div ref={endRef} />
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-xs text-v2-text-secondary px-1">
            <FileText className="w-3.5 h-3.5" />
            <button type="button" onClick={() => router.push('/lessons')} className="hover:text-v2-accent transition-colors">
              {t('open_lessons')}
            </button>
            <span>·</span>
            <ClipboardCheck className="w-3.5 h-3.5" />
            <button type="button" onClick={() => router.push('/assessment-studio')} className="hover:text-v2-accent transition-colors">
              {t('open_assessment')}
            </button>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void send()
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('placeholder')}
              disabled={busy}
              className="flex-1 bg-v2-surface border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="inline-flex items-center justify-center gap-1.5 px-4 h-12 rounded-xl bg-v2-accent text-v2-inverted text-sm font-semibold hover:bg-white transition-colors disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </DashboardLayout>
  )
}