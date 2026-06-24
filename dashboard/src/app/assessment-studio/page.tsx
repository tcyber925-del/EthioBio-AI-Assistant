'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  ClipboardCheck, FileText, Brain, BarChart3,
  Plus, X, Loader2, ExternalLink,
} from 'lucide-react'

import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId, isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

const TOPICS = [
  'Photosynthesis', 'Respiration', 'Genetics', 'Cell Division',
  'Ecology', 'Evolution', 'Classification', 'Circulatory System',
  'Digestive System', 'Nervous System', 'Reproduction',
]

export default function AssessmentStudioPage() {
  const router = useRouter()
  const userId = getUserId()

  const [showDiagnostic, setShowDiagnostic] = useState(false)
  const [diagGrade, setDiagGrade] = useState(10)
  const [diagTopics, setDiagTopics] = useState<string[]>([])
  const [diagCount, setDiagCount] = useState(3)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  const toggleTopic = (topic: string) => {
    setDiagTopics(prev =>
      prev.includes(topic) ? prev.filter(t => t !== topic) : [...prev, topic]
    )
  }

  const runDiagnostic = async () => {
    if (diagTopics.length === 0) return
    setGenerating(true)
    setResult(null)
    try {
      const data = await fetchWithAuth('/quiz/diagnostic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          grade_level: diagGrade,
          topics: diagTopics,
          questions_per_topic: diagCount,
        }),
      }, 180000)
      const topicSummary = data.topic_baselines
        .map((t: any) => `${t.topic} (${t.total} questions)`)
        .join(', ')
      setResult(
        `✅ Diagnostic created for Grade ${data.grade_level}: ${topicSummary}. `
        + `Overall severity: ${data.overall_severity}. `
        + `Submit answers via POST /quiz/submit with the quiz IDs to get baseline scores.`
      )
      setShowDiagnostic(false)
    } catch (err: any) {
      setResult(`❌ ${err.message}`)
    } finally {
      setGenerating(false)
    }
  }

  if (!isAuthenticated()) {
    router.push('/login')
    return null
  }

  return (
    <DashboardLayout breadcrumbs={[
      { label: 'Overview', href: '/v2/overview' },
      { label: 'Assessment Studio' },
    ]}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Assessment Studio</h1>
          <p className="text-sm text-foreground-muted mt-1">Create diagnostics, exit tickets, and manage assessments</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowDiagnostic(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors"
          >
            <Plus className="w-4 h-4" /> Diagnostic
          </button>
          <Link
            href="/quizzes"
            className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg text-sm text-foreground hover:bg-background-secondary transition-colors"
          >
            <ClipboardCheck className="w-4 h-4" /> Quizzes
          </Link>
        </div>
      </div>

      {result && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm flex items-center justify-between ${
          result.startsWith('✅')
            ? 'bg-green-500/10 text-green-400 border border-green-500/20'
            : 'bg-red-500/10 text-red-400 border border-red-500/20'
        }`}>
          <span>{result}</span>
          <button onClick={() => setResult(null)} className="ml-3 hover:opacity-70">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <Link href="/copilot" className="block bg-card rounded-xl border border-border p-6 hover:border-primary/30 transition-colors group">
          <div className="p-3 rounded-xl bg-primary/10 text-primary w-fit mb-4 group-hover:scale-110 transition-transform">
            <Brain className="w-6 h-6" />
          </div>
          <h3 className="font-semibold text-foreground mb-1">Teacher Copilot</h3>
          <p className="text-sm text-foreground-muted">Ask for assessments, quizzes, and exit tickets in natural language</p>
          <span className="inline-flex items-center gap-1 mt-3 text-xs text-primary font-medium">
            Open Copilot <ExternalLink className="w-3 h-3" />
          </span>
        </Link>

        <div className="bg-card rounded-xl border border-border p-6">
          <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400 w-fit mb-4">
            <FileText className="w-6 h-6" />
          </div>
          <h3 className="font-semibold text-foreground mb-1">Exit Tickets</h3>
          <p className="text-sm text-foreground-muted mb-3">3-question checks at the end of each lesson</p>
          <p className="text-xs text-foreground-muted/60">
            Use <code className="px-1 py-0.5 rounded bg-background-secondary text-xs">generate_exit_ticket: true</code> in
            the lesson plan API to auto-generate exit tickets.
          </p>
        </div>

        <Link href="/quizzes" className="block bg-card rounded-xl border border-border p-6 hover:border-primary/30 transition-colors group">
          <div className="p-3 rounded-xl bg-amber-500/10 text-amber-400 w-fit mb-4 group-hover:scale-110 transition-transform">
            <ClipboardCheck className="w-6 h-6" />
          </div>
          <h3 className="font-semibold text-foreground mb-1">Quiz Bank</h3>
          <p className="text-sm text-foreground-muted">Browse, generate, and manage all quizzes</p>
          <span className="inline-flex items-center gap-1 mt-3 text-xs text-primary font-medium">
            View Quizzes <ExternalLink className="w-3 h-3" />
          </span>
        </Link>
      </div>

      <div className="bg-card rounded-xl border border-border p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <BarChart3 className="w-5 h-5 text-primary" />
          <h2 className="text-lg font-semibold text-foreground">Assessment Types</h2>
        </div>
        <div className="overflow-hidden">
          <table className="w-full">
            <thead className="bg-background-secondary">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Description</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Endpoint</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              <tr className="hover:bg-background-secondary/50">
                <td className="px-4 py-3 text-sm font-medium text-foreground">Diagnostic</td>
                <td className="px-4 py-3 text-sm text-foreground-muted">Multi-topic baseline pre-test</td>
                <td className="px-4 py-3"><code className="px-2 py-0.5 rounded bg-background-secondary text-xs text-primary">POST /quiz/diagnostic</code></td>
                <td className="px-4 py-3"><span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400">Live</span></td>
              </tr>
              <tr className="hover:bg-background-secondary/50">
                <td className="px-4 py-3 text-sm font-medium text-foreground">Quiz</td>
                <td className="px-4 py-3 text-sm text-foreground-muted">Standard LLM-generated quiz</td>
                <td className="px-4 py-3"><code className="px-2 py-0.5 rounded bg-background-secondary text-xs text-primary">POST /quiz/generate</code></td>
                <td className="px-4 py-3"><span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400">Live</span></td>
              </tr>
              <tr className="hover:bg-background-secondary/50">
                <td className="px-4 py-3 text-sm font-medium text-foreground">Adaptive Quiz</td>
                <td className="px-4 py-3 text-sm text-foreground-muted">IRT-based adaptive difficulty</td>
                <td className="px-4 py-3"><code className="px-2 py-0.5 rounded bg-background-secondary text-xs text-primary">POST /quiz/generate</code></td>
                <td className="px-4 py-3"><span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-500/10 text-green-400">Live</span></td>
              </tr>
              <tr className="hover:bg-background-secondary/50">
                <td className="px-4 py-3 text-sm font-medium text-foreground">Exit Ticket</td>
                <td className="px-4 py-3 text-sm text-foreground-muted">3-question end-of-lesson check</td>
                <td className="px-4 py-3"><code className="px-2 py-0.5 rounded bg-background-secondary text-xs text-primary">POST /lesson-plan/generate</code></td>
                <td className="px-4 py-3"><span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400">Live</span></td>
              </tr>
              <tr className="hover:bg-background-secondary/50">
                <td className="px-4 py-3 text-sm font-medium text-foreground">Teacher Copilot</td>
                <td className="px-4 py-3 text-sm text-foreground-muted">NL assessment creation via chat</td>
                <td className="px-4 py-3"><code className="px-2 py-0.5 rounded bg-background-secondary text-xs text-primary">POST /copilot/query</code></td>
                <td className="px-4 py-3"><span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400">Live</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {showDiagnostic && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowDiagnostic(false)}>
          <div className="bg-card border border-border rounded-xl shadow-xl p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-foreground">New Diagnostic Assessment</h2>
              <button onClick={() => setShowDiagnostic(false)} className="text-foreground-muted hover:text-foreground transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-foreground-muted block mb-1">Grade Level</label>
                <select
                  value={diagGrade}
                  onChange={e => setDiagGrade(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  {[7, 8, 9, 10, 11, 12].map(g => <option key={g} value={g}>Grade {g}</option>)}
                </select>
              </div>

              <div>
                <label className="text-sm text-foreground-muted block mb-1">Questions per Topic</label>
                <input
                  type="number" min={1} max={10} value={diagCount}
                  onChange={e => setDiagCount(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label className="text-sm text-foreground-muted block mb-2">Topics to Assess</label>
                <div className="flex flex-wrap gap-2">
                  {TOPICS.map(topic => (
                    <button
                      key={topic}
                      onClick={() => toggleTopic(topic)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                        diagTopics.includes(topic)
                          ? 'bg-primary text-white border-primary'
                          : 'bg-background-secondary text-foreground-muted border-border hover:border-primary/50'
                      }`}
                    >
                      {topic}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={runDiagnostic}
                disabled={generating || diagTopics.length === 0}
                className="w-full py-3 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
              >
                {generating ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Generating Diagnostic...</>
                ) : (
                  <>Generate Diagnostic ({diagTopics.length} topics)</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  )
}
