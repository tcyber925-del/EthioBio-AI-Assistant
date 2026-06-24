'use client'

import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import {
  AlertTriangle, Brain, Loader2, SendHorizonal, Sparkles,
  User, GraduationCap, Target, BookOpen, HelpCircle, ClipboardList,
} from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'

interface EvidenceItem {
  source: string
  confidence: number
  content: Record<string, unknown>
}

interface CopilotMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  intent?: string
  intent_confidence?: number
  evidence?: EvidenceItem[]
  confidence?: number
  timestamp: Date
}

const INTENT_ICONS: Record<string, typeof Sparkles> = {
  student_analysis: User,
  classroom_analysis: GraduationCap,
  intervention_guidance: Target,
  curriculum_analysis: BookOpen,
  lesson_planning: ClipboardList,
  assessment_creation: HelpCircle,
}

const INTENT_LABELS: Record<string, string> = {
  student_analysis: 'Student Analysis',
  classroom_analysis: 'Classroom Analysis',
  intervention_guidance: 'Intervention',
  curriculum_analysis: 'Curriculum',
  lesson_planning: 'Lesson Planning',
  assessment_creation: 'Assessment',
}

function IntentBadge({ intent, confidence }: { intent: string; confidence?: number }) {
  const Icon = INTENT_ICONS[intent] || Brain
  const label = INTENT_LABELS[intent] || intent
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-v2-accent/10 text-v2-accent border border-v2-accent/20">
      <Icon size={12} />
      {label}
      {confidence !== undefined && (
        <span className="opacity-60">{(confidence * 100).toFixed(0)}%</span>
      )}
    </span>
  )
}

const EXAMPLE_PROMPTS = [
  'Why is Hana struggling with cell biology?',
  'Who needs attention in Grade 10 Biology?',
  'What intervention should I try for weak students?',
  'Create a lesson plan for photosynthesis',
  'What topics come after mitosis in the curriculum?',
]

export default function CopilotPage() {
  const t = useTranslations('common')
  const [messages, setMessages] = useState<CopilotMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showExamples, setShowExamples] = useState(true)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return

    setShowExamples(false)

    const userMsg: CopilotMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const data = await fetchWithTimeout('/api/copilot/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      }, 60000)

      const assistantMsg: CopilotMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.response || data.reasoning || 'No response generated.',
        intent: data.intent,
        intent_confidence: data.intent_confidence,
        evidence: data.evidence,
        confidence: data.confidence,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err: unknown) {
      const errorMsg: CopilotMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: err instanceof Error ? err.message : 'Request failed',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3rem)] max-w-4xl mx-auto px-4 py-4">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-xl bg-v2-accent/10 flex items-center justify-center">
          <Brain size={18} className="text-v2-accent" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-v2-text">Teacher Copilot</h1>
          <p className="text-xs text-v2-text-secondary">Educational intelligence for your classroom</p>
        </div>
      </div>

      <div
        ref={listRef}
        className="flex-1 overflow-y-auto space-y-4 pb-4 scroll-smooth"
      >
        {messages.length === 0 && showExamples && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-v2-accent/10 flex items-center justify-center mb-4">
              <Sparkles size={28} className="text-v2-accent" />
            </div>
            <p className="text-sm text-v2-text-secondary mb-6 max-w-md">
              Ask anything about your students, classroom, or curriculum.
              Copilot analyzes educational data to provide actionable insights.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
              {EXAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => sendMessage(prompt)}
                  className="text-left text-sm text-v2-text-secondary bg-v2-surface border border-v2-border rounded-xl px-3 py-2.5 hover:border-v2-accent/30 hover:text-v2-text transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-1' : 'order-1'}`}>
              {msg.role === 'assistant' && msg.intent && (
                <div className="mb-1.5 ml-1">
                  <IntentBadge intent={msg.intent} confidence={msg.intent_confidence} />
                </div>
              )}
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-v2-accent text-white rounded-br-md'
                    : 'bg-v2-surface border border-v2-border rounded-bl-md text-v2-text'
                }`}
              >
                {msg.content}
              </div>
              {msg.role === 'assistant' && msg.evidence && msg.evidence.length > 0 && (
                <details className="mt-1 ml-1">
                  <summary className="text-xs text-v2-text-secondary cursor-pointer hover:text-v2-text">
                    {msg.evidence.length} evidence source{msg.evidence.length > 1 ? 's' : ''}
                  </summary>
                  <div className="mt-1 space-y-1">
                    {msg.evidence.map((e, i) => (
                      <div key={i} className="text-xs text-v2-text-secondary bg-v2-bg rounded-lg px-2.5 py-1.5">
                        <span className="font-medium text-v2-text">
                          [{e.source}]
                        </span>{' '}
                        confidence: {(e.confidence * 100).toFixed(0)}%
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-v2-surface border border-v2-border rounded-2xl rounded-bl-md px-4 py-3">
              <Loader2 size={18} className="animate-spin text-v2-accent" />
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-v2-border pt-3 mt-auto">
        <form
          onSubmit={(e) => { e.preventDefault(); sendMessage(input) }}
          className="flex items-center gap-2 bg-v2-surface border border-v2-border rounded-2xl px-4 py-2 focus-within:border-v2-accent/50 transition-colors"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your classroom..."
            className="flex-1 bg-transparent text-sm text-v2-text placeholder-v2-text-tertiary outline-none"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="w-8 h-8 rounded-xl bg-v2-accent text-white flex items-center justify-center disabled:opacity-30 transition-opacity shrink-0"
          >
            <SendHorizonal size={16} />
          </button>
        </form>
      </div>
    </div>
  )
}
