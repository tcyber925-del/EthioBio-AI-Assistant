'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  Sparkles, Target, BookOpen, ClipboardList, FileCheck,
  MessageSquare, BarChart3, Flame, Zap, AlertTriangle,
  RefreshCw, Clock, ChevronRight,
} from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'
import { CardSkeleton } from '@/components/Skeleton'

interface LearningCardData {
  id: string
  title: string
  description: string
  action_type: string
  priority_score: number
  estimated_minutes: number
  xp_reward: number | null
  metadata: Record<string, unknown>
}

interface FeedSummaryData {
  estimated_minutes: number
  xp_available: number
}

interface ContinueLearningFeedData {
  user_id: string
  generated_at: string
  primary_action: LearningCardData | null
  sections: Record<string, LearningCardData[]>
  summary: FeedSummaryData
}

const SECTION_LABELS: Record<string, string> = {
  recovery_actions: 'Recovery Tasks',
  review_actions: 'Review Topics',
  quiz_opportunities: 'Quiz Opportunities',
  tutor_actions: 'Tutor Sessions',
}

const ACTION_ICONS: Record<string, { icon: typeof Target; color: string }> = {
  complete_recovery_task: { icon: ClipboardList, color: 'text-orange-400 bg-orange-500/10' },
  take_quiz: { icon: FileCheck, color: 'text-green-400 bg-green-500/10' },
  exam_practice: { icon: FileCheck, color: 'text-green-400 bg-green-500/10' },
  review_topic: { icon: BookOpen, color: 'text-blue-400 bg-blue-500/10' },
  read_content: { icon: BookOpen, color: 'text-blue-400 bg-blue-500/10' },
  study_diagram: { icon: BarChart3, color: 'text-purple-400 bg-purple-500/10' },
  ask_tutor: { icon: MessageSquare, color: 'text-cyan-400 bg-cyan-500/10' },
  revise_misconception: { icon: MessageSquare, color: 'text-cyan-400 bg-cyan-500/10' },
  maintain_streak: { icon: Flame, color: 'text-yellow-400 bg-yellow-500/10' },
}

const DEFAULT_ICON = { icon: Target, color: 'text-foreground-muted bg-border/50' }

function getActionLink(card: LearningCardData): string {
  switch (card.action_type) {
    case 'complete_recovery_task':
      return '/recovery/'
    case 'take_quiz':
    case 'exam_practice':
      return '/quizzes/'
    case 'review_topic':
    case 'read_content':
      return '/lessons/'
    case 'study_diagram':
      return '/diagrams/'
    case 'ask_tutor':
    case 'revise_misconception':
    case 'maintain_streak':
      return '/ask/'
    default:
      return '#'
  }
}

export default function ContinueLearningFeed({ userId }: { userId: string }) {
  const [feed, setFeed] = useState<ContinueLearningFeedData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchFeed = async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await fetchWithTimeout(`/intelligence/continue-learning/${userId}`)
      setFeed(d)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchFeed() }, [userId])

  if (loading) return <CardSkeleton />

  if (error) {
    return (
      <div className="bg-card rounded-xl border border-border p-5 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-sm text-red-400 mb-2">{error}</p>
        <button onClick={fetchFeed} className="text-xs text-primary hover:underline flex items-center gap-1 mx-auto">
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      </div>
    )
  }

  const hasContent = feed?.primary_action || Object.keys(feed?.sections || {}).length > 0

  if (!hasContent) {
    return (
      <div className="bg-card rounded-xl border border-border p-5 text-center">
        <Sparkles className="w-8 h-8 text-primary mx-auto mb-2" />
        <p className="text-sm text-foreground font-medium mb-1">Start Your Learning Journey</p>
        <p className="text-xs text-foreground-muted mb-3">Take a quiz to get personalized recommendations</p>
        <Link
          href="/quizzes/"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-primary text-white text-xs font-medium rounded-lg hover:bg-primary-hover transition-colors"
        >
          <FileCheck className="w-3.5 h-3.5" /> Start with a Quiz
        </Link>
      </div>
    )
  }

  const sectionOrder = ['recovery_actions', 'review_actions', 'quiz_opportunities', 'tutor_actions']
  const activeSections = sectionOrder.filter(s => (feed!.sections[s]?.length || 0) > 0)

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
        <Target className="w-4 h-4 text-primary" /> Continue Learning
      </h3>

      {feed!.primary_action && (
        <LearningCardComponent card={feed!.primary_action} highlighted />
      )}

      {activeSections.map(sectionKey => (
        <div key={sectionKey} className="mt-4">
          <h4 className="text-xs font-semibold text-foreground-muted uppercase tracking-wider mb-2">
            {SECTION_LABELS[sectionKey] || sectionKey} ({feed!.sections[sectionKey].length})
          </h4>
          <div className="space-y-2">
            {feed!.sections[sectionKey].map(card => (
              <LearningCardComponent key={card.id} card={card} />
            ))}
          </div>
        </div>
      ))}

      <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs text-foreground-muted">
        <span className="flex items-center gap-1">
          <Clock className="w-3 h-3" /> {feed!.summary.estimated_minutes} min
        </span>
        <span className="flex items-center gap-1">
          <Zap className="w-3 h-3 text-yellow-400" /> {feed!.summary.xp_available} XP
        </span>
      </div>
    </div>
  )
}

function LearningCardComponent({ card, highlighted = false }: { card: LearningCardData; highlighted?: boolean }) {
  const cfg = ACTION_ICONS[card.action_type] || DEFAULT_ICON
  const Icon = cfg.icon
  const href = getActionLink(card)

  return (
    <Link
      href={href}
      className={`block rounded-lg p-3 transition-colors group ${
        highlighted
          ? 'bg-primary/5 border border-primary/20 hover:bg-primary/10'
          : 'bg-background-secondary/50 border border-border/50 hover:bg-border/30'
      }`}
    >
      <div className="flex items-start gap-2.5">
        <div className={`p-1.5 rounded-lg ${cfg.color} shrink-0`}>
          <Icon className="w-3.5 h-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className={`text-xs font-medium truncate ${highlighted ? 'text-primary' : 'text-foreground'}`}>
            {card.title}
          </p>
          <p className="text-[11px] text-foreground-muted mt-0.5 line-clamp-1">{card.description}</p>
          <p className="text-[10px] text-foreground-muted/60 mt-1">
            {card.estimated_minutes} min
            {card.xp_reward != null && ` \u00b7 ${card.xp_reward} XP`}
          </p>
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-foreground-muted/40 group-hover:text-foreground-muted transition-colors shrink-0 mt-1" />
      </div>
    </Link>
  )
}
