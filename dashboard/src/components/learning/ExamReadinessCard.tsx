'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw, TrendingUp } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { fetchWithTimeout } from '@/lib/fetch'

interface TopicReadiness {
  topic: string
  readiness_score: number
  risk_level: string
  risk_factors: string[]
  review_status: string
  forgetting_risk?: number | null
}

interface Intervention {
  topic: string
  priority: number
  action_type: string
  estimated_impact: number
  reason: string
}

interface ExamReadinessProfile {
  overall_readiness: number
  readiness_band: string
  projected_exam_score: number
  confidence_score: number
  topic_readiness: TopicReadiness[]
  risk_topics: string[]
  recommended_interventions: Intervention[]
}

function readinessColor(band: string): string {
  switch (band) {
    case 'Strong': return 'text-green-400'
    case 'Ready': return 'text-emerald-400'
    case 'Developing': return 'text-yellow-400'
    default: return 'text-red-400'
  }
}

function readinessBg(band: string): string {
  switch (band) {
    case 'Strong': return 'bg-green-500/10 border-green-500/20'
    case 'Ready': return 'bg-emerald-500/10 border-emerald-500/20'
    case 'Developing': return 'bg-yellow-500/10 border-yellow-500/20'
    default: return 'bg-red-500/10 border-red-500/20'
  }
}

function riskBadgeColor(level: string): string {
  switch (level) {
    case 'CRITICAL': return 'bg-red-500/20 text-red-400'
    case 'HIGH': return 'bg-orange-500/20 text-orange-400'
    case 'MODERATE': return 'bg-yellow-500/20 text-yellow-400'
    default: return 'bg-green-500/20 text-green-400'
  }
}

function forgettingBarColor(risk: number): string {
  if (risk > 0.6) return 'bg-red-500'
  if (risk > 0.3) return 'bg-yellow-500'
  return 'bg-green-500'
}

function actionBadgeStyle(actionType: string): string {
  switch (actionType) {
    case 'REVISE_MISCONCEPTION': return 'bg-purple-500/20 text-purple-400'
    case 'REVIEW_TOPIC': return 'bg-blue-500/20 text-blue-400'
    default: return 'bg-gray-500/20 text-gray-400'
  }
}

export default function ExamReadinessCard({ userId }: { userId: string }) {
  const [data, setData] = useState<ExamReadinessProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    fetchWithTimeout(`/intelligence/readiness/${userId}`)
      .then(d => setData(d))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [userId])

  if (loading) return <CardSkeleton />

  if (error) return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-2 text-red-400 mb-2">
        <AlertTriangle className="w-4 h-4" />
        <span className="text-sm font-medium">Unable to load readiness data</span>
      </div>
      <button onClick={load} className="text-xs text-primary hover:underline flex items-center gap-1">
        <RefreshCw className="w-3 h-3" /> Retry
      </button>
    </div>
  )

  if (!data || data.topic_readiness.length === 0) return (
    <div className="bg-card rounded-xl border border-border p-5">
      <p className="text-sm font-semibold text-foreground mb-2">Exam Readiness</p>
      <p className="text-xs text-foreground-muted">No readiness data yet — take quizzes to assess your readiness.</p>
    </div>
  )

  return (
    <div className={`bg-card rounded-xl border p-5 ${readinessBg(data.readiness_band)}`}>
      <div className="flex items-center gap-2 mb-2">
        <p className="text-sm font-semibold text-foreground">Exam Readiness</p>
        {data.confidence_score < 0.7 && (
          <span className="text-[10px] text-foreground-muted bg-foreground-muted/10 px-1.5 py-0.5 rounded">
            low confidence
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-3 mb-1">
        <span className={`text-3xl font-bold ${readinessColor(data.readiness_band)}`}>
          {Math.round(data.overall_readiness)}%
        </span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${readinessBg(data.readiness_band)} ${readinessColor(data.readiness_band)}`}>
          {data.readiness_band}
        </span>
      </div>

      {data.projected_exam_score > 0 && (
        <div className="flex items-center gap-1.5 mb-3 text-xs text-foreground-muted">
          <TrendingUp className="w-3 h-3" />
          <span>Projected: <strong className="text-foreground">{Math.round(data.projected_exam_score)}%</strong></span>
        </div>
      )}

      <p className="text-xs text-foreground-muted mb-2">
        {data.topic_readiness.length} topic{data.topic_readiness.length > 1 ? 's' : ''} evaluated
      </p>

      {data.risk_topics.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-foreground-muted mb-1.5">Risk Topics</p>
          <div className="flex flex-wrap gap-1.5">
            {data.risk_topics.map(topic => {
              const tr = data.topic_readiness.find(t => t.topic === topic)
              return (
                <div key={topic} className="flex flex-col gap-1 w-full">
                  <div className="flex items-center justify-between">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${riskBadgeColor(tr?.risk_level || 'MODERATE')}`}>
                      {topic}
                    </span>
                    {tr?.forgetting_risk != null && (
                      <span className="text-[10px] text-foreground-muted">
                        forget risk: {(tr.forgetting_risk * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  {tr?.forgetting_risk != null && (
                    <div className="w-full h-1.5 bg-foreground-muted/10 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${forgettingBarColor(tr.forgetting_risk)}`}
                        style={{ width: `${tr.forgetting_risk * 100}%` }}
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {data.recommended_interventions.length > 0 && (
        <div>
          <p className="text-xs font-medium text-foreground-muted mb-1.5">Recommended Actions</p>
          <div className="flex flex-col gap-1.5">
            {data.recommended_interventions.slice(0, 3).map((int, i) => (
              <div key={i} className="text-xs bg-background/50 rounded-lg p-2 border border-border/50">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${actionBadgeStyle(int.action_type)}`}>
                    {int.action_type.replace(/_/g, ' ')}
                  </span>
                  <span className="text-foreground-muted">
                    +{int.estimated_impact} pts
                  </span>
                </div>
                <p className="text-foreground-muted/80">{int.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
