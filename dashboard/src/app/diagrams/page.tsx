'use client'

import { useState } from 'react'
import { Image, Send, Loader2, AlertTriangle } from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'

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

const TOPICS = ['cells', 'organ systems', 'genetics', 'anatomy']
const DIFFICULTIES = ['beginner', 'intermediate', 'advanced']

export default function DiagramsPage() {
  const [prompt, setPrompt] = useState('')
  const [topic, setTopic] = useState('cells')
  const [difficulty, setDifficulty] = useState('beginner')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DiagramResponse | null>(null)
  const [hoveredLabel, setHoveredLabel] = useState<string | null>(null)

  const generateDiagram = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await fetchWithTimeout('/diagram/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          topic,
          difficulty,
        }),
      }, 120000)
      setResult(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
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
          <h1 className="text-2xl font-bold text-foreground">Diagrams</h1>
          <p className="text-sm text-foreground-muted mt-1">Generate and explore biology diagrams with labeled structures</p>
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border p-5 mb-6">
        <div className="grid grid-cols-5 gap-3 mb-4">
          <div>
            <label className="text-xs text-foreground-muted block mb-1.5">Topic</label>
            <select value={topic} onChange={e => setTopic(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
              {TOPICS.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-foreground-muted block mb-1.5">Difficulty</label>
            <select value={difficulty} onChange={e => setDifficulty(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
              {DIFFICULTIES.map(d => <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>)}
            </select>
          </div>
          <div className="col-span-3">
            <label className="text-xs text-foreground-muted block mb-1.5">Prompt</label>
            <div className="flex gap-3">
              <input
                type="text"
                value={prompt}
                onChange={e => setPrompt(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && generateDiagram()}
                placeholder="e.g., 'Label the parts of a plant cell'"
                className="flex-1 px-4 py-2 border border-border rounded-lg text-sm bg-background text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                onClick={generateDiagram}
                disabled={loading || !prompt.trim()}
                className="px-6 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
              >
                {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</> : <><Send className="w-4 h-4" /> Generate</>}
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
          <p className="text-sm text-foreground-muted mt-4">Generating {topic} diagram...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-5 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5" />
          <div>
            <p className="font-medium text-red-400">Error</p>
            <p className="text-sm text-red-400/80 mt-1">{error}</p>
          </div>
        </div>
      )}

      {result && !loading && (
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
                      {hoveredLabel === label.id && (
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
      )}

      {!result && !loading && !error && (
        <div className="text-center py-16">
          <Image className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">Generate a diagram to get started</p>
          <p className="text-sm text-foreground-muted/60 mt-1">Choose a topic, set difficulty, and describe what you want to see</p>
        </div>
      )}
    </div>
  )
}
