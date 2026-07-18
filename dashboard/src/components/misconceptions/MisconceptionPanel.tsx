'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { AlertTriangle, Check, RefreshCw, Flame, CheckCircle } from 'lucide-react'

interface MisconceptionDetail {
  id: string
  topic: string
  pattern_type: string
  description: string
  severity: string
  frequency: number
  confidence: number
  common_wrong_answer: string | null
  last_detected_at: string | null
  resolved: boolean
}

interface MisconceptionTopicSummary {
  topic: string
  count: number
  patterns: MisconceptionDetail[]
}

interface MisconceptionProfile {
  total_patterns: number
  unresolved_count: number
  by_topic: MisconceptionTopicSummary[]
  frequent_patterns: MisconceptionDetail[]
  improvement_trend: string
}

export function MisconceptionPanel({ userId }: { userId: string }) {
  const [profile, setProfile] = useState<MisconceptionProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [resolvingId, setResolvingId] = useState<string | null>(null)
  const [resolvingTopic, setResolvingTopic] = useState<string | null>(null)

  const fetchProfile = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithAuth(`/api/misconceptions/${userId}/profile`)
      setProfile(data)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch misconception profile')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProfile()
  }, [userId])

  const handleResolvePattern = async (patternId: string) => {
    setResolvingId(patternId)
    try {
      await fetchWithAuth(`/api/misconceptions/${patternId}/resolve`, {
        method: 'POST',
      })
      await fetchProfile()
    } catch (err: any) {
      setError(err.message || 'Failed to resolve misconception')
    } finally {
      setResolvingId(null)
    }
  }

  const handleResolveTopic = async (topic: string) => {
    setResolvingTopic(topic)
    try {
      await fetchWithAuth(`/api/misconceptions/resolve-topic/${userId}/${encodeURIComponent(topic)}`, {
        method: 'POST',
      })
      await fetchProfile()
    } catch (err: any) {
      setError(err.message || 'Failed to resolve topic misconceptions')
    } finally {
      setResolvingTopic(null)
    }
  }

  if (loading && !profile) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-6 h-6 animate-spin text-v2-accent" />
      </div>
    )
  }

  if (error && !profile) {
    return (
      <div className="p-5 border border-v2-error/30 bg-v2-error/10 text-v2-error rounded-xl flex items-center gap-3">
        <AlertTriangle className="w-5 h-5 shrink-0" />
        <div className="flex-1 text-sm">{error}</div>
        <button onClick={fetchProfile} className="p-1 hover:bg-v2-error/20 rounded-lg">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    )
  }

  if (!profile || profile.total_patterns === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 border border-dashed border-v2-border rounded-[20px] bg-v2-surface/20 text-center p-6">
        <CheckCircle className="w-10 h-10 text-v2-success mb-2" />
        <h3 className="text-base font-bold text-v2-text-primary">No misconceptions detected</h3>
        <p className="text-xs text-v2-text-secondary mt-1 max-w-xs">
          The student has demonstrated clear understanding across all assessed biology topics so far.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Metrics Strips */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-v2-surface border border-v2-border p-4 rounded-[20px]">
          <p className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold">Total Patterns</p>
          <p className="verge-display text-2xl text-v2-text-primary mt-1">{profile.total_patterns}</p>
        </div>
        <div className="bg-v2-surface border border-v2-border p-4 rounded-[20px]">
          <p className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold">Active Unresolved</p>
          <p className={`verge-display text-2xl mt-1 ${profile.unresolved_count > 0 ? 'text-v2-error' : 'text-v2-success'}`}>
            {profile.unresolved_count}
          </p>
        </div>
        <div className="bg-v2-surface border border-v2-border p-4 rounded-[20px]">
          <p className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold">Trend</p>
          <p className="text-sm font-bold text-v2-accent mt-2 flex items-center gap-1">
            <Flame className="w-4 h-4 shrink-0" /> {profile.improvement_trend || 'Neutral'}
          </p>
        </div>
      </div>

      {/* Main breakdown by topic */}
      <div className="flex flex-col gap-5">
        <h3 className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold border-b border-v2-border/30 pb-2">
          Breakdown by Topic
        </h3>

        {profile.by_topic.map((summary) => (
          <div key={summary.topic} className="bg-v2-surface border border-v2-border rounded-[20px] p-5 flex flex-col gap-4">
            {/* Topic header */}
            <div className="flex items-center justify-between border-b border-v2-border/20 pb-2.5">
              <div>
                <h4 className="text-base font-bold text-v2-text-primary">{summary.topic}</h4>
                <p className="text-xs text-v2-text-secondary mt-0.5">{summary.count} active patterns</p>
              </div>
              {summary.patterns.some(p => !p.resolved) && (
                <button
                  onClick={() => handleResolveTopic(summary.topic)}
                  disabled={resolvingTopic === summary.topic}
                  className="px-3 h-8 rounded-xl border border-v2-accent text-v2-accent hover:bg-v2-accent hover:text-v2-bg text-xs font-semibold transition-all flex items-center gap-1"
                >
                  {resolvingTopic === summary.topic ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                  Resolve Topic
                </button>
              )}
            </div>

            {/* Topic patterns list */}
            <div className="flex flex-col gap-3">
              {summary.patterns.map((p) => (
                <div key={p.id} className="bg-v2-bg/40 border border-v2-border/30 rounded-xl p-4 flex flex-col sm:flex-row justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-v2-text-primary">
                        {p.pattern_type || 'Concept Gap'}
                      </span>
                      <span className={`text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full ${
                        p.severity === 'critical' ? 'bg-v2-error/10 text-v2-error border border-v2-error/20' :
                        p.severity === 'misunderstanding' ? 'bg-v2-warning/10 text-v2-warning border border-v2-warning/20' :
                        'bg-v2-accent-muted text-v2-accent border border-v2-accent/20'
                      }`}>
                        {p.severity}
                      </span>
                      <span className="text-[10px] text-v2-text-secondary">
                        Logged {p.frequency}x
                      </span>
                    </div>

                    <p className="text-sm text-v2-text-primary mt-2 leading-relaxed italic">
                      "{p.description}"
                    </p>

                    {p.common_wrong_answer && (
                      <p className="text-xs text-v2-text-secondary mt-2 bg-v2-surface p-2.5 rounded-lg border border-v2-border/40">
                        <strong className="text-v2-text-primary">Wrong Answer:</strong> "{p.common_wrong_answer}"
                      </p>
                    )}
                  </div>

                  <div className="shrink-0 flex items-center justify-end">
                    {p.resolved ? (
                      <span className="text-xs text-v2-success font-semibold flex items-center gap-1 bg-v2-success/10 px-2.5 py-1 rounded-xl">
                        <Check className="w-3.5 h-3.5" /> Resolved
                      </span>
                    ) : (
                      <button
                        onClick={() => handleResolvePattern(p.id)}
                        disabled={resolvingId === p.id}
                        className="px-3.5 h-9 rounded-xl bg-v2-accent/10 border border-v2-accent/30 text-v2-accent hover:bg-v2-accent hover:text-v2-bg text-xs font-bold transition-all flex items-center gap-1.5"
                      >
                        {resolvingId === p.id ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Check className="w-3.5 h-3.5" />
                        )}
                        Resolve
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
