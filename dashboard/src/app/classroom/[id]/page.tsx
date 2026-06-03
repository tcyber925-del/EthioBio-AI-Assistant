'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { AlertTriangle, ArrowLeft, RefreshCw, School, TrendingUp } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

interface StudentRisk {
  student_id: string
  readiness_score: number
  risk_level: string
  risk_factors: string[]
  recommended_action: string
}

interface Intervention {
  topic: string
  priority: number
  action_type: string
  estimated_impact: number
  reason: string
}

interface ClassroomProfile {
  classroom_id: string
  total_students: number
  classroom_health: number
  readiness_distribution: Record<string, number>
  risk_students: StudentRisk[]
  intervention_candidates: Intervention[]
  mastery_heatmap: Record<string, number>
}

function healthColor(score: number): string {
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-emerald-400'
  if (score >= 40) return 'text-yellow-400'
  return 'text-red-400'
}

function healthBg(score: number): string {
  if (score >= 80) return 'bg-green-500/10 border-green-500/20'
  if (score >= 60) return 'bg-emerald-500/10 border-emerald-500/20'
  if (score >= 40) return 'bg-yellow-500/10 border-yellow-500/20'
  return 'bg-red-500/10 border-red-500/20'
}

function riskBadgeColor(level: string): string {
  switch (level) {
    case 'CRITICAL': return 'bg-red-500/20 text-red-400'
    case 'HIGH': return 'bg-orange-500/20 text-orange-400'
    case 'MODERATE': return 'bg-yellow-500/20 text-yellow-400'
    default: return 'bg-green-500/20 text-green-400'
  }
}

function heatmapColor(score: number): string {
  if (score >= 80) return 'bg-green-500/20 text-green-400'
  if (score >= 60) return 'bg-emerald-500/20 text-emerald-400'
  if (score >= 40) return 'bg-yellow-500/20 text-yellow-400'
  return 'bg-red-500/20 text-red-400'
}

export default function ClassroomOverviewPage() {
  const params = useParams()
  const router = useRouter()
  const classroomId = params.id as string

  const [data, setData] = useState<ClassroomProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    load()
  }, [classroomId])

  const load = () => {
    setLoading(true)
    setError(null)
    fetchWithAuth(`/teacher/classrooms/${classroomId}/overview`)
      .then(d => setData(d))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  if (loading) return <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}</div>

  if (error) return (
    <div className="text-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-red-400">{error}</p>
      <button onClick={load} className="text-sm text-primary hover:underline mt-3 flex items-center gap-1 mx-auto">
        <RefreshCw className="w-3 h-3" /> Retry
      </button>
    </div>
  )

  if (!data || data.total_students === 0) return (
    <div className="text-center py-16">
      <School className="w-12 h-12 text-border mx-auto mb-3" />
      <p className="text-foreground-muted font-medium">No classroom data yet</p>
      <p className="text-sm text-foreground-muted/60 mt-1">Enroll students to see classroom intelligence.</p>
      <Link href="/classroom" className="text-sm text-primary hover:underline mt-4 inline-block">
        Back to classrooms
      </Link>
    </div>
  )

  const dist = data.readiness_distribution
  const totalDist = Object.values(dist).reduce((a, b) => a + b, 0)

  return (
    <div>
      <Link href="/classroom" className="flex items-center gap-2 text-sm text-foreground-muted hover:text-foreground mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to classrooms
      </Link>

      {/* Health Score */}
      <div className={`bg-card rounded-xl border p-6 mb-6 ${healthBg(data.classroom_health)}`}>
        <div className="flex items-center gap-2 mb-1">
          <TrendingUp className="w-5 h-5 text-foreground-muted" />
          <h2 className="text-lg font-semibold text-foreground">Classroom Health</h2>
        </div>
        <div className="flex items-baseline gap-3">
          <span className={`text-5xl font-bold ${healthColor(data.classroom_health)}`}>
            {Math.round(data.classroom_health)}%
          </span>
          <span className="text-sm text-foreground-muted">{data.total_students} students</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Readiness Distribution */}
          <div className="bg-card rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3">Readiness Distribution</h3>
            {totalDist === 0 ? (
              <p className="text-xs text-foreground-muted">No readiness data available.</p>
            ) : (
              <div className="space-y-2">
                {[
                  { band: 'Strong', color: 'bg-green-500', text: 'text-green-400' },
                  { band: 'Ready', color: 'bg-emerald-500', text: 'text-emerald-400' },
                  { band: 'Developing', color: 'bg-yellow-500', text: 'text-yellow-400' },
                  { band: 'Critical', color: 'bg-red-500', text: 'text-red-400' },
                ].map(({ band, color, text }) => {
                  const count = dist[band] || 0
                  const pct = totalDist > 0 ? (count / totalDist) * 100 : 0
                  return (
                    <div key={band} className="flex items-center gap-3">
                      <span className={`text-xs w-20 font-medium ${text}`}>{band}</span>
                      <div className="flex-1 h-3 bg-foreground-muted/10 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-foreground-muted w-8 text-right">{count}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Mastery Heatmap */}
          <div className="bg-card rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3">Topic Heatmap</h3>
            {Object.keys(data.mastery_heatmap).length === 0 ? (
              <p className="text-xs text-foreground-muted">No topic data available yet.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {Object.entries(data.mastery_heatmap).sort((a, b) => a[1] - b[1]).map(([topic, score]) => (
                  <div key={topic} className={`rounded-lg px-3 py-2 text-center ${heatmapColor(score)}`}>
                    <p className="text-xs font-medium truncate">{topic}</p>
                    <p className="text-lg font-bold">{Math.round(score)}%</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Risk Students */}
          <div className="bg-card rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3">
              At-Risk Students ({data.risk_students.length})
            </h3>
            {data.risk_students.length === 0 ? (
              <p className="text-xs text-foreground-muted">No students at risk — all on track.</p>
            ) : (
              <div className="space-y-2">
                {data.risk_students.sort((a, b) => a.readiness_score - b.readiness_score).map(s => (
                  <div key={s.student_id} className="flex items-center justify-between bg-background/50 rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-foreground">Student #{s.student_id.slice(0, 8)}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${riskBadgeColor(s.risk_level)}`}>
                        {s.risk_level}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-foreground-muted">{Math.round(s.readiness_score)}% readiness</span>
                      <span className="text-[10px] text-primary bg-primary/10 px-2 py-0.5 rounded">
                        {s.recommended_action.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          {/* Intervention Queue */}
          <div className="bg-card rounded-xl border border-border p-5">
            <h3 className="text-sm font-semibold text-foreground mb-3">Intervention Queue</h3>
            {data.intervention_candidates.length === 0 ? (
              <p className="text-xs text-foreground-muted">No interventions needed — all students on track.</p>
            ) : (
              <div className="space-y-2">
                {data.intervention_candidates.slice(0, 10).map((int, i) => (
                  <div key={i} className="text-xs bg-background/50 rounded-lg p-2.5 border border-border/50">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-foreground truncate max-w-[120px]">{int.topic}</span>
                      <span className="text-foreground-muted">+{int.estimated_impact} pts</span>
                    </div>
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                        {int.action_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-foreground-muted">{(int.priority * 100).toFixed(0)}% priority</span>
                    </div>
                    <p className="text-foreground-muted/70">{int.reason}</p>
                  </div>
                ))}
                {data.intervention_candidates.length > 10 && (
                  <p className="text-xs text-foreground-muted text-center mt-2">
                    +{data.intervention_candidates.length - 10} more
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
