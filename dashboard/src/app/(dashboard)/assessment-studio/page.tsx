'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'
import ModelSelector from '@/components/ModelSelector'
import { Sparkles, AlertCircle, RefreshCw, Eye, Check, Loader2, Layers, Award } from 'lucide-react'
import Link from 'next/link'

interface Quiz {
  id: string
  title: string
  grade_level: number
  topic: string
  question_count: number
  status: string
  created_at: string
}

interface Question {
  question_type: string
  question_text: string
  options: string[] | null
  correct_answer: string
  explanation: string | null
  difficulty: string
}

export default function AssessmentStudioPage() {
  const router = useRouter()
  const [quizzes, setQuizzes] = useState<Quiz[]>([])
  const [loadingList, setLoadingList] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Generation States
  const [grade, setGrade] = useState(10)
  const [topic, setTopic] = useState('')
  const [assessmentType, setAssessmentType] = useState('mastery')
  const [adaptive, setAdaptive] = useState(false)
  const [count, setCount] = useState(5)
  const [selectedTypes, setSelectedTypes] = useState<string[]>(['multiple_choice'])
  const [selectedModel, setSelectedModel] = useState('')
  const [generating, setGenerating] = useState(false)
  
  // Preview State
  const [previewQuestions, setPreviewQuestions] = useState<Question[] | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const fetchQuizzes = async () => {
    setLoadingList(true)
    try {
      const response = await fetchWithAuth('/api/admin/content/review?type=quiz&status=published')
      const data = await response.json()
      setQuizzes(data.items || [])
    } catch (err: any) {
      console.error(err)
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    fetchQuizzes()
  }, [router])

  const handleTypeToggle = (type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    )
  }

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!topic.trim()) return
    setGenerating(true)
    setError(null)
    setPreviewQuestions(null)
    setSuccessMsg(null)

    try {
      const payload = {
        grade_level: grade,
        topic: topic,
        question_count: count,
        assessment_type: assessmentType,
        types: selectedTypes.length > 0 ? selectedTypes : ['multiple_choice'],
        model: selectedModel,
        adaptive: adaptive,
      }

      const genResponse = await fetchWithAuth('/quiz/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const { task_id } = await genResponse.json()

      let task: any
      for (let i = 0; i < 120; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const taskResponse = await fetchWithAuth(`/quiz/generate/status/${task_id}`)
        task = await taskResponse.json()
        if (task.status === 'completed') break
        if (task.status === 'failed') throw new Error(task.error || 'Generation failed')
      }
      if (!task || task.status !== 'completed') throw new Error('Generation timed out')
      setSuccessMsg(`Successfully generated new ${assessmentType} assessment!`)
      fetchQuizzes()
    } catch (err: any) {
      setError(err.message || 'Failed to generate assessment')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <DashboardLayout breadcrumbs={[{ label: 'Assessment Studio', href: '/assessment-studio' }, { label: 'Builder' }]}>
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div>
          <h1 className="verge-display text-4xl text-v2-text-primary leading-none">Assessment Studio</h1>
          <p className="text-sm text-v2-text-secondary mt-1">
            Construct high-fidelity quizzes, diagnostic items, and adaptive biology assessments.
          </p>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {successMsg && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-success/10 border border-v2-success/30 text-v2-success text-sm">
            <Check className="w-5 h-5 shrink-0" />
            <div className="flex-1">{successMsg}</div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Builder Form */}
          <div className="lg:col-span-2 flex flex-col gap-5 bg-v2-surface border border-v2-border p-6 rounded-[20px]">
            <h2 className="text-lg font-bold text-v2-text-primary flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-v2-accent" /> Assessment Builder
            </h2>

            <form onSubmit={handleGenerate} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                {/* Grade */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-v2-text-secondary uppercase font-semibold">Grade Level</label>
                  <select
                    value={grade}
                    onChange={e => setGrade(Number(e.target.value))}
                    className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-3 py-2 outline-none focus:border-v2-accent"
                  >
                    {[7, 8, 9, 10, 11, 12].map(g => (
                      <option key={g} value={g} className="bg-v2-surface">Grade {g}</option>
                    ))}
                  </select>
                </div>

                {/* Assessment Type */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-v2-text-secondary uppercase font-semibold">Diagnostic Type</label>
                  <select
                    value={assessmentType}
                    onChange={e => setAssessmentType(e.target.value)}
                    className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-3 py-2 outline-none focus:border-v2-accent"
                  >
                    <option value="mastery" className="bg-v2-surface">Mastery Quiz</option>
                    <option value="diagnostic" className="bg-v2-surface">Diagnostic Assessment</option>
                    <option value="readiness" className="bg-v2-surface">Exam Readiness</option>
                    <option value="misconception" className="bg-v2-surface">Misconception Probe</option>
                    <option value="intervention" className="bg-v2-surface">Intervention Validation</option>
                  </select>
                </div>
              </div>

              {/* Topic */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">Biology Topic</label>
                <input
                  type="text"
                  value={topic}
                  onChange={e => setTopic(e.target.value)}
                  placeholder="e.g. Aerobic Respiration, Mitosis vs Meiosis, Protein Synthesis"
                  required
                  disabled={generating}
                  className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-3.5 py-2.5 outline-none focus:border-v2-accent"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Count */}
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-v2-text-secondary uppercase font-semibold">Question Count ({count})</label>
                  <input
                    type="range"
                    min={3}
                    max={15}
                    step={1}
                    value={count}
                    onChange={e => setCount(Number(e.target.value))}
                    className="accent-v2-accent bg-v2-bg rounded-lg h-2 mt-2"
                  />
                </div>

                {/* Adaptive */}
                <div className="flex items-center gap-2.5 mt-6 pl-2">
                  <input
                    type="checkbox"
                    id="adaptive"
                    checked={adaptive}
                    onChange={e => setAdaptive(e.target.checked)}
                    className="accent-v2-accent w-4 h-4 rounded"
                  />
                  <label htmlFor="adaptive" className="text-xs text-v2-text-secondary uppercase font-semibold cursor-pointer">
                    Adapt to Student Profile
                  </label>
                </div>
              </div>

              {/* Question Formats */}
              <div className="flex flex-col gap-2">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">Question Types</label>
                <div className="flex gap-3 flex-wrap">
                  {[
                    { id: 'multiple_choice', label: 'Multiple Choice' },
                    { id: 'true_false', label: 'True / False' },
                    { id: 'short_answer', label: 'Short Answer' },
                    { id: 'diagram_label', label: 'Diagram Labeling' },
                  ].map(t => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => handleTypeToggle(t.id)}
                      className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all ${
                        selectedTypes.includes(t.id)
                          ? 'bg-v2-accent-muted text-v2-accent border-v2-accent/40'
                          : 'bg-v2-bg text-v2-text-secondary border-v2-border hover:border-v2-accent/30'
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Model selection */}
              <div className="flex flex-col gap-1">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">LLM Generator Model</label>
                <ModelSelector value={selectedModel} onChange={setSelectedModel} />
              </div>

              {/* Generate button */}
              <button
                type="submit"
                disabled={generating || !topic.trim()}
                className="mt-2 h-12 rounded-xl bg-v2-accent text-v2-inverted text-sm font-bold hover:bg-white disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
              >
                {generating ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" /> Generating Assessment...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" /> Create Assessment
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Assessment Library */}
          <div className="flex flex-col gap-4 bg-v2-surface border border-v2-border p-6 rounded-[20px] h-fit">
            <h2 className="text-lg font-bold text-v2-text-primary flex items-center gap-2">
              <Layers className="w-5 h-5 text-v2-accent" /> Generated Library
            </h2>

            {loadingList ? (
              <div className="py-12 flex justify-center">
                <RefreshCw className="w-5 h-5 animate-spin text-v2-text-secondary" />
              </div>
            ) : quizzes.length > 0 ? (
              <div className="flex flex-col gap-3">
                {quizzes.slice(0, 8).map(q => (
                  <div key={q.id} className="flex items-center justify-between p-3 bg-v2-bg/40 border border-v2-border rounded-xl">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-v2-text-primary truncate">{q.title}</p>
                      <p className="text-xs text-v2-text-secondary mt-0.5">
                        Grade {q.grade_level} · {q.question_count} items
                      </p>
                    </div>
                    <Link
                      href={`/quizzes/${q.id}`}
                      className="p-1.5 border border-v2-border hover:border-v2-accent rounded-lg text-v2-text-secondary hover:text-v2-accent transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                    </Link>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-v2-text-secondary text-center py-8">
                No published assessments in this library.
              </p>
            )}
          </div>
        </div>

        {/* Live Preview Section */}
        {previewQuestions && (
          <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4">
            <h2 className="text-lg font-bold text-v2-text-primary flex items-center gap-2 border-b border-v2-border/40 pb-2.5">
              <Award className="w-5 h-5 text-v2-accent" /> Assessment Preview & Key
            </h2>

            <div className="flex flex-col gap-4">
              {previewQuestions.map((q, idx) => (
                <div key={idx} className="bg-v2-bg/30 border border-v2-border/30 rounded-xl p-5 flex flex-col gap-3">
                  <div className="flex items-center justify-between flex-wrap gap-2 text-xs">
                    <span className="font-semibold text-v2-accent uppercase">Item #{idx + 1} ({q.question_type})</span>
                    <span className="text-v2-text-secondary px-2 py-0.5 rounded-full border border-v2-border">
                      Difficulty: {q.difficulty}
                    </span>
                  </div>
                  
                  <p className="text-sm font-semibold text-v2-text-primary leading-relaxed">
                    {q.question_text}
                  </p>

                  {q.options && q.options.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pl-2">
                      {q.options.map((opt, oIdx) => (
                        <div key={oIdx} className="text-xs text-v2-text-secondary bg-v2-surface/50 p-2.5 rounded border border-v2-border/20">
                          {opt}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-2 bg-v2-accent-muted p-3.5 rounded-xl border border-v2-accent/20 flex flex-col gap-1.5">
                    <p className="text-xs text-v2-accent font-bold">CORRECT ANSWER</p>
                    <p className="text-sm text-v2-text-primary font-medium">{q.correct_answer}</p>
                    {q.explanation && (
                      <>
                        <p className="text-xs text-v2-accent font-bold mt-1.5">EXPLANATION</p>
                        <p className="text-xs text-v2-text-secondary leading-relaxed">{q.explanation}</p>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
