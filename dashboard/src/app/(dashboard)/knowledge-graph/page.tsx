'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'
import { BookOpen, RefreshCw, AlertCircle, Plus, Trash2, CheckCircle2 } from 'lucide-react'

interface CurriculumTopic {
  id: string
  grade_level: number
  unit: string
  topic: string
  subtopic: string | null
}

interface GraphNode {
  node_id: string
  topic: string
  unit: string
  grade_level: number
  relationship_type: string
  depth: number
}

interface GapItem {
  node_id: string
  topic: string
  unit: string
  grade_level: number
  relationship_type: string
  depth: number
  user_score: number | null
}

interface Student {
  id: string
  telegram_id: number | null
  role: string
}

export default function KnowledgeGraphPage() {
  const router = useRouter()
  
  // Data States
  const [topics, setTopics] = useState<CurriculumTopic[]>([])
  const [students, setStudents] = useState<Student[]>([])
  const [prereqChain, setPrereqChain] = useState<GraphNode[]>([])
  const [dependentChain, setDependentChain] = useState<GraphNode[]>([])
  const [gapAnalysis, setGapAnalysis] = useState<GapItem[]>([])

  // Selector States
  const [selectedTopicId, setSelectedTopicId] = useState<string>('')
  const [selectedStudentId, setSelectedStudentId] = useState<string>('')
  const [newPrereqTopicId, setNewPrereqTopicId] = useState<string>('')

  // UI States
  const [loading, setLoading] = useState(true)
  const [loadingGraph, setLoadingGraph] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const fetchVersion = useRef(0)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const activeTopic = topics.find(t => t.id === selectedTopicId)

  // Fetch initial topics and students
  const fetchInitialData = async () => {
    setLoading(true)
    setError(null)
    try {
      const topicResponse = await fetchWithAuth('/api/ekg/topics')
      const topicData = await topicResponse.json()
      setTopics(topicData)

      // Pre-select first topic if available
      if (topicData.length > 0) {
        setSelectedTopicId(topicData[0].id)
      }

      // Try to load students for gap analysis
      try {
        const studentResponse = await fetchWithAuth('/api/admin/dashboard')
        const studentData = await studentResponse.json()
        setStudents(studentData.recent_users?.filter((u: any) => u.role === 'student') || [])
      } catch {
        // Suppress failure, default to empty students list
        setStudents([])
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load curriculum topics')
    } finally {
      setLoading(false)
    }
  }

  // Fetch EKG chains for selected topic
  const fetchGraphChains = async (topicId: string, studentId: string) => {
    if (!topicId) return
    const version = ++fetchVersion.current
    setLoadingGraph(true)
    setError(null)
    try {
      const prereqsResponse = await fetchWithAuth(`/api/ekg/chain/${topicId}/prerequisites?max_depth=3`)
      const prereqs = await prereqsResponse.json()
      if (version !== fetchVersion.current) return
      setPrereqChain(prereqs)

      const dependentsResponse = await fetchWithAuth(`/api/ekg/chain/${topicId}/dependents?max_depth=3`)
      const dependents = await dependentsResponse.json()
      if (version !== fetchVersion.current) return
      setDependentChain(dependents)

      if (studentId) {
        const gapsResponse = await fetchWithAuth(`/api/ekg/gap-analysis/${topicId}/${studentId}`)
        const gaps = await gapsResponse.json()
        if (version !== fetchVersion.current) return
        setGapAnalysis(gaps)
      } else {
        setGapAnalysis([])
      }
    } catch (err: any) {
      console.error(err)
      setError('Could not retrieve dependency paths')
    } finally {
      setLoadingGraph(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    fetchInitialData()
  }, [router])

  useEffect(() => {
    if (selectedTopicId) {
      fetchGraphChains(selectedTopicId, selectedStudentId)
    }
  }, [selectedTopicId, selectedStudentId])

  const handleAddPrerequisite = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedTopicId || !newPrereqTopicId) return
    if (selectedTopicId === newPrereqTopicId) {
      setError('A topic cannot be a prerequisite of itself')
      return
    }

    setSubmitting(true)
    setError(null)
    setSuccess(null)
    try {
      await fetchWithAuth('/api/ekg/prerequisites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic_id: selectedTopicId,
          prerequisite_topic_id: newPrereqTopicId,
          relationship_type: 'prerequisite',
        }),
      })
      setSuccess('Prerequisite relationship added successfully!')
      setNewPrereqTopicId('')
      fetchGraphChains(selectedTopicId, selectedStudentId)
    } catch (err: any) {
      setError(err.message || 'Failed to establish relationship')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeletePrerequisite = async (prereqId: string) => {
    if (deleting) return
    if (!confirm('Are you sure you want to remove this prerequisite relationship?')) return
    setDeleting(prereqId)
    setError(null)
    setSuccess(null)
    try {
      // Find the edge in topic prerequisites list
      const prereqsResponse = await fetchWithAuth(`/api/ekg/prerequisites/${selectedTopicId}`)
      const prereqs = await prereqsResponse.json()
      const matching = prereqs.find((p: any) => p.prerequisite_topic_id === prereqId)
      if (!matching) {
        setDeleting(null)
        throw new Error('Relationship edge not found')
      }
      await fetchWithAuth(`/api/ekg/prerequisites/${matching.id}`, {
        method: 'DELETE',
      })
      setSuccess('Prerequisite relationship removed!')
      fetchGraphChains(selectedTopicId, selectedStudentId)
    } catch (err: any) {
      setError(err.message || 'Failed to remove relationship')
    } finally {
      setDeleting(null)
    }
  }

  // Visual Node Coordinates layout math
  const leftNodes = prereqChain.filter(n => n.depth === 1)
  const rightNodes = dependentChain.filter(n => n.depth === 1)

  const leftCount = leftNodes.length
  const rightCount = rightNodes.length
  const maxColumnNodes = Math.max(leftCount, rightCount, 1)

  // Height sizing
  const nodeHeight = 85
  const gapHeight = 25
  const boxHeight = maxColumnNodes * (nodeHeight + gapHeight) + 40
  const canvasHeight = Math.max(boxHeight, 280)

  const centerY = canvasHeight / 2

  return (
    <DashboardLayout breadcrumbs={[{ label: 'Knowledge Graph', href: '/knowledge-graph' }, { label: 'Interactive Map' }]}>
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="verge-display text-4xl text-v2-text-primary leading-none">Curriculum Knowledge Graph</h1>
            <p className="text-sm text-v2-text-secondary mt-1">
              Visualize semantic prerequisite paths and identify learner mastery gaps.
            </p>
          </div>
          <button
            onClick={fetchInitialData}
            className="p-2.5 bg-v2-surface border border-v2-border hover:border-v2-accent rounded-xl text-v2-text-primary transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Global Notifications */}
        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-success/10 border border-v2-success/30 text-v2-success text-sm">
            <CheckCircle2 className="w-5 h-5 shrink-0" />
            <div className="flex-1">{success}</div>
          </div>
        )}

        {loading ? (
          <div className="py-20 flex justify-center">
            <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Control Sidebar Panel */}
            <div className="lg:col-span-1 flex flex-col gap-5 bg-v2-surface border border-v2-border p-6 rounded-[20px] h-fit">
              {/* Topic Select */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">Active Curriculum Topic</label>
                <select
                  value={selectedTopicId}
                  onChange={e => setSelectedTopicId(e.target.value)}
                  className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-3.5 py-2.5 outline-none focus:border-v2-accent w-full"
                >
                  {topics.map(t => (
                    <option key={t.id} value={t.id} className="bg-v2-surface">
                      Grade {t.grade_level} - Unit {t.unit}: {t.topic}
                    </option>
                  ))}
                </select>
              </div>

              {/* Student Gap analysis Selector */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">Student Gap Profiler</label>
                <select
                  value={selectedStudentId}
                  onChange={e => setSelectedStudentId(e.target.value)}
                  className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-3.5 py-2.5 outline-none focus:border-v2-accent w-full"
                >
                  <option value="" className="bg-v2-surface">-- No Student Selected (Reference Mode) --</option>
                  {students.map(s => (
                    <option key={s.id} value={s.id} className="bg-v2-surface">
                      Student ID: {s.telegram_id || s.id.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Add prerequisite form */}
              <form onSubmit={handleAddPrerequisite} className="border-t border-v2-border/40 pt-4 flex flex-col gap-3">
                <h3 className="text-sm font-bold text-v2-text-primary flex items-center gap-2">
                  <Plus className="w-4 h-4 text-v2-accent" /> Connect Prerequisite
                </h3>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] text-v2-text-secondary uppercase font-semibold">Select Prerequisite Topic</label>
                  <select
                    value={newPrereqTopicId}
                    onChange={e => setNewPrereqTopicId(e.target.value)}
                    required
                    className="bg-v2-bg border border-v2-border text-v2-text-primary text-xs rounded-xl px-3 py-2 outline-none focus:border-v2-accent w-full"
                  >
                    <option value="" className="bg-v2-surface">-- Select Topic --</option>
                    {topics
                      .filter(t => t.id !== selectedTopicId)
                      .map(t => (
                        <option key={t.id} value={t.id} className="bg-v2-surface">
                          Grade {t.grade_level} - Unit {t.unit}: {t.topic}
                        </option>
                      ))}
                  </select>
                </div>
                <button
                  type="submit"
                  disabled={submitting || !newPrereqTopicId}
                  className="h-10 rounded-xl bg-v2-accent text-v2-inverted text-xs font-bold hover:bg-white disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5"
                >
                  {submitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                  Establish Relationship
                </button>
              </form>
            </div>

            {/* Visual Canvas Panel */}
            <div className="lg:col-span-2 bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4 relative overflow-hidden min-h-[360px]">
              <h2 className="text-lg font-bold text-v2-text-primary flex items-center gap-2 border-b border-v2-border/30 pb-2.5">
                <BookOpen className="w-5 h-5 text-v2-accent" /> Interactive Relationship Map
              </h2>

              {loadingGraph ? (
                <div className="absolute inset-0 bg-v2-surface/70 backdrop-blur-[1px] flex items-center justify-center z-10">
                  <RefreshCw className="w-6 h-6 animate-spin text-v2-accent" />
                </div>
              ) : null}

              {/* Responsive SVG Layout */}
              <div className="relative border border-v2-border/30 rounded-xl bg-v2-bg/30 overflow-auto">
                <svg width="100%" height={canvasHeight} style={{ minWidth: '700px' }} className="block">
                  {/* Define markers for arrows */}
                  <defs>
                    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                      <path d="M 0 1 L 10 5 L 0 9 z" fill="rgba(255,255,255,0.25)" />
                    </marker>
                  </defs>

                  {/* Draw Bezier connector curves */}
                  {leftNodes.map((n, idx) => {
                    const fromY = leftCount === 1 ? centerY : (idx * (nodeHeight + gapHeight)) + 70
                    const toY = centerY
                    return (
                      <path
                        key={`edge-left-${n.node_id}`}
                        d={`M 220 ${fromY} C 290 ${fromY}, 290 ${toY}, 360 ${toY}`}
                        fill="none"
                        stroke="rgba(60, 255, 208, 0.2)"
                        strokeWidth="2"
                        markerEnd="url(#arrow)"
                      />
                    )
                  })}

                  {rightNodes.map((n, idx) => {
                    const fromY = centerY
                    const toY = rightCount === 1 ? centerY : (idx * (nodeHeight + gapHeight)) + 70
                    return (
                      <path
                        key={`edge-right-${n.node_id}`}
                        d={`M 480 ${fromY} C 550 ${fromY}, 550 ${toY}, 620 ${toY}`}
                        fill="none"
                        stroke="rgba(255, 255, 255, 0.15)"
                        strokeWidth="2"
                        markerEnd="url(#arrow)"
                      />
                    )
                  })}

                  {/* SVG HTML overlays nested using foreignObject */}
                  
                  {/* LEFT COLUMN: UPSTREAM PREREQUISITES */}
                  {leftNodes.map((n, idx) => {
                    const y = leftCount === 1 ? centerY - 38 : (idx * (nodeHeight + gapHeight)) + 32
                    const gap = gapAnalysis.find(g => g.node_id === n.node_id)
                    const isGap = selectedStudentId && gap !== undefined
                    const scoreText = gap?.user_score !== null && gap?.user_score !== undefined ? `${(gap.user_score * 100).toFixed(0)}%` : '0%'

                    return (
                      <foreignObject key={`node-left-${n.node_id}`} x="20" y={y} width="200" height="76">
                        <div className={`p-2.5 rounded-xl border flex flex-col gap-0.5 justify-center h-full transition-all text-left bg-v2-surface ${
                          isGap ? 'border-v2-error bg-v2-error/10 text-v2-error' : 'border-v2-border bg-v2-surface hover:border-v2-accent'
                        }`}>
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] text-v2-text-secondary font-semibold uppercase">Prerequisite</span>
                            {selectedStudentId && (
                              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${
                                isGap ? 'bg-v2-error/20 text-v2-error' : 'bg-v2-success/20 text-v2-success'
                              }`}>
                                {isGap ? `Gap (${scoreText})` : 'Mastered'}
                              </span>
                            )}
                          </div>
                          <p className="text-xs font-bold text-v2-text-primary truncate">{n.topic}</p>
                          <div className="flex justify-between items-center mt-1">
                            <span className="text-[10px] text-v2-text-secondary">Grade {n.grade_level}</span>
                            <button
                              onClick={() => handleDeletePrerequisite(n.node_id)}
                              disabled={!!deleting}
                              className="text-v2-text-secondary hover:text-v2-error p-0.5 transition-colors disabled:opacity-40"
                              title="Delete Prerequisite"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </foreignObject>
                    )
                  })}

                  {leftNodes.length === 0 && (
                    <foreignObject x="20" y={centerY - 38} width="200" height="76">
                      <div className="border border-dashed border-v2-border/40 rounded-xl flex items-center justify-center p-3 text-center text-[11px] text-v2-text-secondary h-full bg-v2-surface/10">
                        No prerequisite topics linked.
                      </div>
                    </foreignObject>
                  )}

                  {/* MIDDLE NODE: ACTIVE SELECTED TOPIC */}
                  {activeTopic && (
                    <foreignObject x="320" y={centerY - 45} width="160" height="90">
                      <div className="p-3.5 rounded-[16px] border-2 border-v2-accent bg-v2-accent/10 flex flex-col justify-center h-full text-center shadow-lg shadow-v2-accent/5">
                        <span className="text-[9px] text-v2-accent font-bold uppercase tracking-wider">Active Focus</span>
                        <p className="text-xs font-extrabold text-v2-text-primary mt-1 line-clamp-2 leading-tight">
                          {activeTopic.topic}
                        </p>
                        <span className="text-[10px] text-v2-text-secondary mt-1">Grade {activeTopic.grade_level} · Unit {activeTopic.unit}</span>
                      </div>
                    </foreignObject>
                  )}

                  {/* RIGHT COLUMN: DOWNSTREAM DEPENDENTS */}
                  {rightNodes.map((n, idx) => {
                    const y = rightCount === 1 ? centerY - 38 : (idx * (nodeHeight + gapHeight)) + 32
                    return (
                      <foreignObject key={`node-right-${n.node_id}`} x="480" y={y} width="200" height="76">
                        <div className="p-2.5 rounded-xl border border-v2-border bg-v2-surface hover:border-v2-accent flex flex-col gap-0.5 justify-center h-full transition-all text-left">
                          <span className="text-[9px] text-v2-text-secondary font-semibold uppercase">Dependent</span>
                          <p className="text-xs font-bold text-v2-text-primary truncate">{n.topic}</p>
                          <span className="text-[10px] text-v2-text-secondary mt-1">Grade {n.grade_level}</span>
                        </div>
                      </foreignObject>
                    )
                  })}

                  {rightNodes.length === 0 && (
                    <foreignObject x="480" y={centerY - 38} width="200" height="76">
                      <div className="border border-dashed border-v2-border/40 rounded-xl flex items-center justify-center p-3 text-center text-[11px] text-v2-text-secondary h-full bg-v2-surface/10">
                        No downstream dependents.
                      </div>
                    </foreignObject>
                  )}
                </svg>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
