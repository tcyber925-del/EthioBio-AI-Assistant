'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { fetchWithTimeout } from '@/lib/fetch'

interface ExamReadinessProfile {
  overall_readiness: number
  readiness_band: string
  topic_readiness: Array<{
    topic: string
    readiness_score: number
    risk_level: string
    risk_factors: string[]
    review_status: string
  }>
  risk_topics: string[]
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
      <p className="text-sm font-semibold text-foreground mb-2">Exam Readiness</p>
      <div className="flex items-baseline gap-2 mb-3">
        <span className={`text-3xl font-bold ${readinessColor(data.readiness_band)}`}>
          {Math.round(data.overall_readiness)}%
        </span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${readinessBg(data.readiness_band)} ${readinessColor(data.readiness_band)}`}>
          {data.readiness_band}
        </span>
      </div>

      <p className="text-xs text-foreground-muted mb-2">
        {data.topic_readiness.length} topic{data.topic_readiness.length > 1 ? 's' : ''} evaluated
      </p>

      {data.risk_topics.length > 0 && (
        <div>
          <p className="text-xs font-medium text-foreground-muted mb-1.5">Risk Topics</p>
          <div className="flex flex-wrap gap-1.5">
            {data.risk_topics.map(topic => (
              <span key={topic} className={`text-xs px-2 py-0.5 rounded-full ${riskBadgeColor(data.topic_readiness.find(t => t.topic === topic)?.risk_level || 'MODERATE')}`}>
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
