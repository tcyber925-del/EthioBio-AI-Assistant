'use client'

import { useState } from 'react'
import { ChevronRight, ChevronDown, AlertTriangle } from 'lucide-react'

interface Misconception {
  pattern_type: string
  description: string
  frequency: number
}

interface WeakTopic {
  topic: string
  unit: string
  grade_level: number
  average_score: number
  attempt_count: number
  severity: string
  confidence: number
  misconceptions: Misconception[]
}

interface LearningTreeProps {
  topics: WeakTopic[]
}

function TopicNode({ topic, defaultOpen }: { topic: WeakTopic; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen)

  const masteryColor =
    topic.average_score < 40 ? 'text-red-400' :
    topic.average_score < 60 ? 'text-yellow-400' :
    'text-green-400'

  const dotColor =
    topic.average_score < 40 ? 'bg-red-400' :
    topic.average_score < 60 ? 'bg-yellow-400' :
    'bg-green-400'

  return (
    <div className="border border-border rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-3 text-left hover:bg-background-secondary/50 transition-colors rounded-lg"
      >
        {open ? <ChevronDown className="w-4 h-4 text-foreground-muted flex-shrink-0" /> : <ChevronRight className="w-4 h-4 text-foreground-muted flex-shrink-0" />}
        <div className={`w-2.5 h-2.5 rounded-full ${dotColor} flex-shrink-0`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate">{topic.topic}</p>
          <p className="text-xs text-foreground-muted truncate">
            {topic.unit && `${topic.unit} · `}Grade {topic.grade_level}
          </p>
        </div>
        <span className={`text-sm font-semibold ${masteryColor}`}>
          {topic.average_score.toFixed(0)}%
        </span>
      </button>
      {open && (
        <div className="px-3 pb-3 pt-0 border-t border-border/50">
          <div className="grid grid-cols-3 gap-3 mt-3">
            <div>
              <p className="text-xs text-foreground-muted">Attempts</p>
              <p className="text-sm font-semibold text-foreground">{topic.attempt_count}</p>
            </div>
            <div>
              <p className="text-xs text-foreground-muted">Confidence</p>
              <p className="text-sm font-semibold text-foreground">{(topic.confidence * 100).toFixed(0)}%</p>
            </div>
            <div>
              <p className="text-xs text-foreground-muted">Severity</p>
              <p className={`text-sm font-semibold capitalize ${masteryColor}`}>{topic.severity}</p>
            </div>
          </div>
          {topic.misconceptions.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-xs font-medium text-foreground-muted mb-2">Misconceptions:</p>
              {topic.misconceptions.map((mc, j) => (
                <div key={j} className="flex items-center gap-2 text-xs text-foreground-muted mb-1">
                  <AlertTriangle className="w-3 h-3 text-yellow-400 flex-shrink-0" />
                  <span>{mc.pattern_type}: {mc.description}</span>
                  <span className="text-foreground-muted/60">({mc.frequency}x)</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function LearningTree({ topics }: LearningTreeProps) {
  if (topics.length === 0) {
    return (
      <div className="text-center py-8 text-foreground-muted text-sm">
        No weak topics to display
      </div>
    )
  }

  const sorted = [...topics].sort((a, b) => a.average_score - b.average_score)

  return (
    <div className="space-y-2">
      {sorted.map((topic, i) => (
        <TopicNode key={i} topic={topic} defaultOpen={i < 2} />
      ))}
    </div>
  )
}
