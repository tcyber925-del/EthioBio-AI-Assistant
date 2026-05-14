'use client'

import { useState } from 'react'
import { Send, MessageSquare, AlertTriangle, BookOpen } from 'lucide-react'

export default function AskPage() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [model, setModel] = useState('')
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
        ? { question: question.trim(), grade_level: grade }
        : { user_id: '00000000-0000-0000-0000-000000000001', question: question.trim(), grade_level: grade, use_rag: true }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (mode === 'graph') {
        setAnswer(data.answer || '')
        setModel(data.model_used || '')
        setConfidence(data.confidence || 0)
        setSources(data.sources || [])
      } else {
        setAnswer(data.answer || '')
        setModel(data.model_used || '')
        setConfidence(data.confidence || 0)
      }
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
          <h1 className="text-2xl font-bold text-gray-900">Ask Q&A</h1>
          <p className="text-sm text-gray-500 mt-1">Test the biology assistant</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={grade} onChange={e => setGrade(Number(e.target.value))} className="px-3 py-2 border rounded-lg text-sm bg-white">
            {[7, 8, 9, 10, 11, 12].map(g => <option key={g} value={g}>Grade {g}</option>)}
          </select>
          <div className="flex border rounded-lg overflow-hidden">
            <button onClick={() => setMode('graph')} className={`px-3 py-2 text-xs font-medium ${mode === 'graph' ? 'bg-green-600 text-white' : 'bg-white text-gray-600'}`}>Graph</button>
            <button onClick={() => setMode('chat')} className={`px-3 py-2 text-xs font-medium ${mode === 'chat' ? 'bg-green-600 text-white' : 'bg-white text-gray-600'}`}>Chat</button>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border p-5 mb-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && askQuestion()}
            placeholder="Ask a biology question (e.g., 'What is DNA replication?')"
            className="flex-1 px-4 py-3 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          />
          <button
            onClick={askQuestion}
            disabled={loading || !question.trim()}
            className="px-6 py-3 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? 'Thinking...' : <><Send className="w-4 h-4" /> Ask</>}
          </button>
        </div>
      </div>

      {loading && (
        <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-gray-200 rounded w-3/4 mx-auto" />
            <div className="h-4 bg-gray-200 rounded w-1/2 mx-auto" />
            <div className="h-4 bg-gray-200 rounded w-2/3 mx-auto" />
          </div>
          <p className="text-sm text-gray-400 mt-4">Calling gemma4:31b-cloud...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5" />
          <div>
            <p className="font-medium text-red-800">Error</p>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        </div>
      )}

      {answer && !loading && (
        <div className="bg-white rounded-xl shadow-sm border p-6">
          <div className="flex items-center gap-2 text-xs text-gray-400 mb-4 pb-3 border-b">
            <MessageSquare className="w-4 h-4" />
            <span className="font-mono">{model}</span>
            <span className="px-2 py-0.5 bg-green-50 text-green-700 rounded-full text-xs">{Math.round(confidence * 100)}% confidence</span>
          </div>
          <p className="text-gray-900 leading-relaxed whitespace-pre-wrap">{answer}</p>
          {sources.length > 0 && (
            <div className="mt-4 pt-3 border-t">
              <p className="text-xs text-gray-400 font-medium mb-2">Sources</p>
              <div className="flex flex-wrap gap-2">
                {sources.map((s, i) => (
                  <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full text-xs">
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
          <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 font-medium">Ask a question to get started</p>
          <p className="text-sm text-gray-400 mt-1">Example: "What is protein synthesis?" or "Explain evolution"</p>
        </div>
      )}
    </div>
  )
}
