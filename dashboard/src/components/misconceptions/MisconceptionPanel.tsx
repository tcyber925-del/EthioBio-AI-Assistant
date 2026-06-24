'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, Brain, CheckCircle, TrendingUp, TrendingDown } from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { motion, AnimatePresence } from 'framer-motion'

interface MisconceptionDetail {
  id: string
  topic: string
  pattern_type: string
  description: string
  frequency: number
  common_wrong_answer?: string | null
  last_detected_at?: string | null
}

interface TopicSummary {
  topic: string
  count: number
  patterns: MisconceptionDetail[]
}

interface MisconceptionProfile {
  total_patterns: number
  unresolved_count: number
  by_topic: TopicSummary[]
  frequent_patterns: MisconceptionDetail[]
  improvement_trend: string
}

export function MisconceptionPanel({ userId }: { userId: string }) {
  const [profile, setProfile] = useState<MisconceptionProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedTopic, setExpandedTopic] = useState<string | null>(null)

  const fetchProfile = async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await fetchWithAuth(`/api/misconceptions/${userId}/profile`)
      setProfile(d)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchProfile() }, [userId])

  if (loading && !profile) {
    return (
      <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)] animate-pulse">
        <div className="h-5 w-36 bg-v2-border rounded mb-4" />
        <div className="h-4 w-48 bg-v2-border rounded mb-2" />
        <div className="h-4 w-32 bg-v2-border rounded" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
        <p className="text-sm text-red-500 flex items-center gap-2">
          <AlertTriangle size={16} /> {error}
        </p>
      </div>
    )
  }

  if (!profile || profile.unresolved_count === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-v2-surface rounded-[20px] border border-v2-border p-6"
      >
        <div className="flex items-center gap-2 mb-1">
          <Brain size={18} className="text-v2-text-secondary" />
          <h3 className="text-sm font-medium text-v2-text-secondary">Misconception Intelligence</h3>
        </div>
        <div className="flex items-center gap-2 mt-3 text-v2-text-tertiary">
          <CheckCircle size={16} className="text-green-500" />
          <p className="text-sm">No unresolved misconceptions. Student understanding is on track.</p>
        </div>
      </motion.div>
    )
  }

  const trendIcon = profile.improvement_trend === 'improving'
    ? <TrendingUp size={16} className="text-green-500" />
    : profile.improvement_trend === 'worsening'
      ? <TrendingDown size={16} className="text-red-500" />
      : null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-v2-surface rounded-[20px] border border-v2-border p-6 shadow-[0_1px_2px_rgba(0,0,0,.04),0_12px_32px_rgba(0,0,0,.06)]"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain size={18} className="text-v2-accent" />
          <h3 className="text-sm font-medium">Misconception Intelligence</h3>
        </div>
        {trendIcon && (
          <span className="flex items-center gap-1 text-xs text-v2-text-secondary">
            {trendIcon} {profile.improvement_trend}
          </span>
        )}
      </div>

      <div className="flex gap-4 mb-4">
        <div className="flex-1 bg-v2-bg rounded-xl p-3">
          <p className="text-2xl font-semibold text-v2-text">{profile.unresolved_count}</p>
          <p className="text-xs text-v2-text-secondary mt-1">Unresolved</p>
        </div>
        <div className="flex-1 bg-v2-bg rounded-xl p-3">
          <p className="text-2xl font-semibold text-v2-text">{profile.total_patterns}</p>
          <p className="text-xs text-v2-text-secondary mt-1">Total patterns</p>
        </div>
        <div className="flex-1 bg-v2-bg rounded-xl p-3">
          <p className="text-2xl font-semibold text-v2-text">{profile.by_topic.length}</p>
          <p className="text-xs text-v2-text-secondary mt-1">Topics affected</p>
        </div>
      </div>

      {profile.frequent_patterns.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-medium text-v2-text-secondary mb-2">Most frequent</p>
          {profile.frequent_patterns.map((p) => (
            <div key={p.id} className="flex items-start gap-2 py-1.5">
              <AlertTriangle size={14} className="text-amber-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm text-v2-text">{p.description}</p>
                <p className="text-xs text-v2-text-secondary">
                  {p.topic} &middot; seen {p.frequency} time{p.frequency !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {profile.by_topic.map((topic) => (
        <div key={topic.topic} className="border-t border-v2-border pt-3 mt-3 first:border-0 first:pt-0 first:mt-0">
          <button
            onClick={() => setExpandedTopic(expandedTopic === topic.topic ? null : topic.topic)}
            className="flex items-center justify-between w-full text-left"
          >
            <span className="text-sm font-medium text-v2-text">{topic.topic}</span>
            <span className="text-xs text-v2-text-secondary bg-v2-bg px-2 py-0.5 rounded-full">
              {topic.count}
            </span>
          </button>
          <AnimatePresence>
            {expandedTopic === topic.topic && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                {topic.patterns.map((p) => (
                  <div key={p.id} className="flex items-start gap-2 py-2 pl-2">
                    <AlertTriangle size={12} className="text-amber-500 mt-1 shrink-0" />
                    <div>
                      <p className="text-sm text-v2-text">{p.description}</p>
                      <p className="text-xs text-v2-text-secondary">
                        frequency {p.frequency}
                        {p.common_wrong_answer ? ` · wrong: "${p.common_wrong_answer}"` : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </motion.div>
  )
}
