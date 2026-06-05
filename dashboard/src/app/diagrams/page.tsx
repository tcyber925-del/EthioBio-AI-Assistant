'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Image, Send, Loader2, AlertTriangle, CheckCircle2, XCircle, RefreshCw } from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'
import { isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface DiagramLabel {
  id: string
  text: string
  x: number
  y: number
}

interface DiagramResponse {
  diagram_svg: string
  labels: DiagramLabel[]
  title: string
  topic: string
  difficulty: string
  model_used: string
}

interface LabelResult {
  label_id: string
  correct_text: string
  submitted_text: string
  is_correct: boolean
  explanation: string
}

interface ValidateResponse {
  score: number
  total_labels: number
  correct_count: number
  results: LabelResult[]
  attempt_id: string
}

interface ModelOption {
  id: string
  name: string
  provider: string
  available: boolean
  is_default: boolean
}

const TOPICS = ['cells', 'organ systems', 'genetics', 'anatomy']
const DIFFICULTIES = ['beginner', 'intermediate', 'advanced']
const PLACEHOLDER_USER_ID = '00000000-0000-0000-0000-000000000001'

export default function DiagramsPage() {
  const router = useRouter()
  const td = useTranslations('diagrams')
  const tc = useTranslations('common')
  const [models, setModels] = useState<ModelOption[]>([])
  const [modelsLoading, setModelsLoading] = useState(true)
  const [prompt, setPrompt] = useState('')
  const [topic, setTopic] = useState('cells')
  const [difficulty, setDifficulty] = useState('beginner')
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModel, setSelectedModel] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DiagramResponse | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [validationResult, setValidationResult] = useState<ValidateResponse | null>(null)
  const [confirmedCorrectIds, setConfirmedCorrectIds] = useState<Set<string>>(new Set())
  const [labelInputs, setLabelInputs] = useState<Record<string, string>>({})
  const [hoveredLabel, setHoveredLabel] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
  }, [router])

  useEffect(() => {
    fetchWithTimeout('/models', { method: 'GET' })
      .then((data: ModelOption[]) => {
        setModels(data)
        const defaultModel = data.find((m: ModelOption) => m.is_default)
        if (defaultModel) {
          setSelectedProvider(defaultModel.provider)
          setSelectedModel(defaultModel.id)
        } else if (data.length > 0) {
          setSelectedProvider(data[0].provider)
          setSelectedModel(data[0].id)
        }
        setModelsLoading(false)
      })
      .catch(() => setModelsLoading(false))
  }, [])

  const generateDiagram = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    setValidationResult(null)
    setConfirmedCorrectIds(new Set())
    setLabelInputs({})

    try {
      const data = await fetchWithTimeout('/diagram/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          topic,
          difficulty,
          model: selectedModel || undefined,
        }),
      }, 120000)
      setResult(data)
      const inputs: Record<string, string> = {}
      data.labels.forEach((l: DiagramLabel) => { inputs[l.id] = '' })
      setLabelInputs(inputs)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const submitLabels = async () => {
    if (!result) return
    setSubmitting(true)
    setValidationResult(null)

    try {
      const submittedLabels = result.labels.map(l => ({
        id: l.id,
        text: labelInputs[l.id]?.trim() || '',
        x: l.x,
        y: l.y,
      }))

      const data = await fetchWithTimeout('/diagram/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: PLACEHOLDER_USER_ID,
          correct_labels: result.labels,
          submitted_labels: submittedLabels,
          topic: result.topic,
          difficulty: result.difficulty,
        }),
      })
      setValidationResult(data)
      setConfirmedCorrectIds(new Set())
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const resetExercise = () => {
    setValidationResult(null)
    if (result && validationResult) {
      const inputs: Record<string, string> = {}
      const confirmed: Set<string> = new Set()
      result.labels.forEach(l => {
        const prev = validationResult.results.find(r => r.label_id === l.id)
        if (prev?.is_correct) {
          confirmed.add(l.id)
          inputs[l.id] = prev.correct_text
        } else {
          inputs[l.id] = ''
        }
      })
      setConfirmedCorrectIds(confirmed)
      setLabelInputs(inputs)
    } else if (result) {
      const inputs: Record<string, string> = {}
      result.labels.forEach(l => { inputs[l.id] = '' })
      setLabelInputs(inputs)
    }
  }

  const getViewBox = (svg: string) => {
    const match = svg.match(/viewBox=["']([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)["']/)
    if (match) return { width: parseFloat(match[3]), height: parseFloat(match[4]) }
    return null
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{td('title')}</h1>
          <p className="text-sm text-foreground-muted mt-1">{td('diagrams_subtitle')}</p>
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border p-5 mb-6">
        <div className="grid grid-cols-6 gap-3 mb-4">
          <div>
            <label className="text-xs text-foreground-muted block mb-1.5">{td('topic')}</label>
            <select value={topic} onChange={e => setTopic(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
              {TOPICS.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-foreground-muted block mb-1.5">{td('difficulty')}</label>
            <select value={difficulty} onChange={e => setDifficulty(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
              {DIFFICULTIES.map(d => <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-foreground-muted block mb-1.5">{td('provider')}</label>
            <select value={selectedProvider} onChange={e => {
              const provider = e.target.value
              setSelectedProvider(provider)
              const first = models.find(m => m.provider === provider)
              setSelectedModel(first ? first.id : '')
            }}
              className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
              disabled={modelsLoading}>
              {Array.from(new Set(models.map(m => m.provider))).map(p =>
                <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
              )}
            </select>
          </div>
          <div>
            <label className="text-xs text-foreground-muted block mb-1.5">{tc('model_label')}</label>
            <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
              disabled={modelsLoading || !selectedProvider}>
              {models
                .filter(m => m.provider === selectedProvider)
                .map(m => (
                  <option key={m.id} value={m.id} disabled={!m.available}>
                    {m.name}{m.is_default ? ' ★' : ''}{!m.available ? ` (${td('not_configured')})` : ''}
                  </option>
                ))}
            </select>
          </div>
          <div className="col-span-3">
            <label className="text-xs text-foreground-muted block mb-1.5">{td('prompt')}</label>
            <div className="flex gap-3">
              <input
                type="text"
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && generateDiagram()}
                placeholder={td('prompt_placeholder')}
                className="flex-1 px-4 py-2 border border-border rounded-lg text-sm bg-background text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                onClick={generateDiagram}
                disabled={loading || !prompt.trim()}
                className="px-6 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
              >
                {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> {td('generating')}...</> : <><Send className="w-4 h-4" /> {td('generate_button')}</>}
              </button>
            </div>
          </div>
        </div>
      </div>

      {loading && (
        <div className="bg-card rounded-xl border border-border p-8 text-center">
          <div className="animate-pulse space-y-3">
            <div className="h-4 bg-border rounded w-3/4 mx-auto" />
            <div className="h-4 bg-border rounded w-1/2 mx-auto" />
            <div className="h-4 bg-border rounded w-2/3 mx-auto" />
          </div>
          <p className="text-sm text-foreground-muted mt-4">{td('generating_topic', { topic })}</p>
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

      {result && !loading && (
        <div className="space-y-6">
          <div className="bg-card rounded-xl border border-border p-6">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
              <div>
                <h2 className="text-lg font-semibold text-foreground">{result.title}</h2>
                <p className="text-xs text-foreground-muted mt-1">
                  {result.topic} &middot; {result.difficulty} &middot; {result.labels.length} label{result.labels.length !== 1 ? 's' : ''}
                  {result.model_used && <> &middot; {result.model_used}</>}
                </p>
              </div>
            </div>

            <div className="relative w-full overflow-hidden rounded-lg">
              <div
                className="w-full [&_svg]:w-full [&_svg]:h-auto"
                dangerouslySetInnerHTML={{ __html: result.diagram_svg }}
              />
              {result.labels.length > 0 && (
                <div className="absolute inset-0 pointer-events-none">
                  {result.labels.map((label, i) => {
                    const vb = getViewBox(result.diagram_svg)
                    if (!vb) return null
                    const pctX = (label.x / vb.width) * 100
                    const pctY = (label.y / vb.height) * 100
                    return (
                      <div
                        key={label.id}
                        className="absolute pointer-events-auto"
                        style={{ left: `${pctX}%`, top: `${pctY}%`, transform: 'translate(-50%, -50%)' }}
                        onMouseEnter={() => setHoveredLabel(label.id)}
                        onMouseLeave={() => setHoveredLabel(null)}
                      >
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all cursor-pointer ${
                          hoveredLabel === label.id
                            ? 'bg-primary text-white scale-125 shadow-lg shadow-primary/40'
                            : 'bg-primary/80 text-white shadow-md'
                        }`}>
                          {i + 1}
                        </div>
                        {hoveredLabel === label.id && !validationResult && (
                          <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-background-secondary text-foreground text-xs px-2.5 py-1.5 rounded-lg border border-border whitespace-nowrap shadow-xl z-10 pointer-events-none">
                            {label.text}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          <div className="bg-card rounded-xl border border-border p-6">
            <h3 className="text-lg font-semibold text-foreground mb-4">{td('label_diagram')}</h3>
            <p className="text-sm text-foreground-muted mb-4">
              {td('label_instruction')}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
              {result.labels.map((label, i) => {
                const valResult = validationResult?.results.find(r => r.label_id === label.id)
                const isCorrect = valResult?.is_correct
                const isRevealed = validationResult !== null
                const isConfirmed = !isRevealed && confirmedCorrectIds.has(label.id)

                return (
                  <div key={label.id} className="flex items-center gap-3">
                    <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                      isConfirmed
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-primary/20 text-primary'
                    }`}>
                      {i + 1}
                    </span>
                    {isConfirmed ? (
                      <div className="flex-1 px-3 py-2 rounded-lg text-sm bg-green-500/10 border border-green-500/30 text-green-400 flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                        <span className="font-medium">{labelInputs[label.id]}</span>
                        <span className="text-xs text-green-400/60 ml-auto">{td('confirmed')}</span>
                      </div>
                    ) : isRevealed ? (
                      <div className={`flex-1 px-3 py-2 rounded-lg text-sm border ${
                        isCorrect
                          ? 'bg-green-500/10 border-green-500/30 text-green-400'
                          : 'bg-red-500/10 border-red-500/30 text-red-400'
                      }`}>
                        <div className="flex items-center gap-2">
                          {isCorrect ? (
                            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                          ) : (
                            <XCircle className="w-4 h-4 flex-shrink-0" />
                          )}
                          <span className={isCorrect ? '' : 'line-through opacity-60'}>
                            {valResult?.submitted_text || td('empty_label')}
                          </span>
                          {!isCorrect && (
                            <span className="text-green-400 ml-1">
                              → {valResult?.correct_text}
                            </span>
                          )}
                        </div>
                        {!isCorrect && valResult?.explanation && (
                          <p className="text-xs text-foreground-muted mt-1 ml-6">{valResult.explanation}</p>
                        )}
                      </div>
                    ) : (
                      <input
                        type="text"
                        value={labelInputs[label.id] || ''}
                        onChange={e => {
                          setLabelInputs(prev => ({ ...prev, [label.id]: e.target.value }))
                        }}
                        onKeyDown={e => {
                          if (e.key === 'Enter') {
                            const entries = Object.entries(labelInputs)
                            const idx = entries.findIndex(([id]) => id === label.id)
                            if (idx < entries.length - 1) {
                              const nextId = entries[idx + 1][0]
                              document.getElementById(`label-input-${nextId}`)?.focus()
                            }
                          }
                        }}
                        id={`label-input-${label.id}`}
                        placeholder={td('enter_label')}
                        className="flex-1 px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary"
                      />
                    )}
                  </div>
                )
              })}
            </div>

            {validationResult && (
              <div className="mb-4 p-4 bg-background rounded-lg border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-lg font-bold text-foreground">
                      {td('score_label', { score: validationResult.score })}
                    </span>
                    <span className="text-sm text-foreground-muted ml-2">
                      {td('correct_count', { correct: validationResult.correct_count, total: validationResult.total_labels })}
                    </span>
                  </div>
                  <button
                    onClick={resetExercise}
                    className="px-4 py-2 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-background-secondary transition-colors flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" /> {td('try_again')}
                  </button>
                </div>
              </div>
            )}

            {!validationResult && (
              <button
                onClick={submitLabels}
                disabled={submitting}
                className="px-6 py-2.5 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
              >
                {submitting ? <><Loader2 className="w-4 h-4 animate-spin" /> {td('validating')}...</> : <><CheckCircle2 className="w-4 h-4" /> {td('submit_labels')}</>}
              </button>
            )}
          </div>
        </div>
      )}

      {!result && !loading && !error && (
        <div className="text-center py-16">
          <Image className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">{td('no_diagrams')}</p>
          <p className="text-sm text-foreground-muted/60 mt-1">{td('no_diagrams_subtitle')}</p>
        </div>
      )}
    </div>
  )
}
