"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  Loader2,
  TrendingDown,
  TrendingUp,
  Users,
} from "lucide-react"
import { fetchWithAuth } from "@/lib/fetchWithAuth"

interface TopicEntry {
  topic: string
  affected_students: number
  total_students: number
  impact_percentage: number
  avg_severity_rank: number
  severity_distribution: Record<string, number>
  top_pattern: string
  top_pattern_frequency: number
}

interface ClassroomHeatmapData {
  classroom_id: string
  total_students: number
  students_with_misconceptions: number
  total_unresolved_patterns: number
  by_topic: TopicEntry[]
  improvement_trend: string
  generated_at: string
}

const SEVERITY_COLORS: Record<string, string> = {
  knowledge_gap: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  misunderstanding: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  misconception: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  persistent_misconception: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
}

const SEVERITY_LABELS: Record<string, string> = {
  knowledge_gap: "Gap",
  misunderstanding: "Partial",
  misconception: "Model",
  persistent_misconception: "Persistent",
}

function severityRank(rank: number): string {
  if (rank >= 3.5) return "text-red-600 dark:text-red-400"
  if (rank >= 2.5) return "text-orange-600 dark:text-orange-400"
  if (rank >= 1.5) return "text-amber-600 dark:text-amber-400"
  return "text-blue-600 dark:text-blue-400"
}

function impactColor(pct: number): string {
  if (pct >= 50) return "bg-red-500"
  if (pct >= 25) return "bg-orange-500"
  if (pct >= 10) return "bg-amber-500"
  return "bg-blue-500"
}

interface MisconceptionHeatmapProps {
  classroomId: string
}

export function MisconceptionHeatmap({ classroomId }: MisconceptionHeatmapProps) {
  const [data, setData] = useState<ClassroomHeatmapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchWithAuth(`/misconceptions/classroom/${classroomId}/heatmap`)
      .then((res: Response) => {
        if (!res.ok) throw new Error(`Failed to load: ${res.status}`)
        return res.json()
      })
      .then((d: ClassroomHeatmapData) => {
        setData(d)
        setLoading(false)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : String(e))
        setLoading(false)
      })
  }, [classroomId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-v2-accent" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 p-4 text-red-600 bg-red-50 dark:bg-red-950/30 rounded-xl">
        <AlertTriangle size={18} />
        <span className="text-sm">{error}</span>
      </div>
    )
  }

  if (!data || data.total_students === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-8 text-v2-muted-foreground">
        <Users size={32} />
        <p className="text-sm">No classroom data available</p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-v2-card p-4 rounded-xl border border-v2-border">
          <div className="flex items-center gap-2 text-v2-muted-foreground text-xs mb-1">
            <Users size={14} />
            <span>Students</span>
          </div>
          <p className="text-2xl font-semibold text-v2-foreground">
            {data.students_with_misconceptions}
            <span className="text-sm text-v2-muted-foreground font-normal ml-1">
              / {data.total_students}
            </span>
          </p>
        </div>

        <div className="bg-v2-card p-4 rounded-xl border border-v2-border">
          <div className="flex items-center gap-2 text-v2-muted-foreground text-xs mb-1">
            <Brain size={14} />
            <span>Patterns</span>
          </div>
          <p className="text-2xl font-semibold text-v2-foreground">
            {data.total_unresolved_patterns}
          </p>
        </div>

        <div className="bg-v2-card p-4 rounded-xl border border-v2-border">
          <div className="flex items-center gap-2 text-v2-muted-foreground text-xs mb-1">
            {data.improvement_trend === "improving" ? (
              <TrendingUp size={14} className="text-green-500" />
            ) : data.improvement_trend === "worsening" ? (
              <TrendingDown size={14} className="text-red-500" />
            ) : (
              <CheckCircle2 size={14} />
            )}
            <span>Trend</span>
          </div>
          <p className="text-2xl font-semibold text-v2-foreground capitalize">
            {data.improvement_trend}
          </p>
        </div>
      </div>

      {data.by_topic.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-8 text-v2-muted-foreground">
          <CheckCircle2 size={32} className="text-green-500" />
          <p className="text-sm">No unresolved misconceptions in this classroom</p>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm font-medium text-v2-foreground">
            Topics by Impact
          </p>
          {data.by_topic.map((topic, i) => (
            <motion.div
              key={topic.topic}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-v2-card p-4 rounded-xl border border-v2-border"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-v2-foreground">
                    {topic.topic}
                  </span>
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${severityRank(topic.avg_severity_rank)} bg-v2-muted`}>
                    {topic.avg_severity_rank.toFixed(1)}
                  </span>
                </div>
                <span className="text-xs text-v2-muted-foreground">
                  {topic.affected_students}/{topic.total_students} students
                </span>
              </div>

              <div className="w-full h-2 bg-v2-muted rounded-full overflow-hidden mb-2">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${impactColor(topic.impact_percentage)}`}
                  style={{ width: `${topic.impact_percentage}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-xs text-v2-muted-foreground">
                <div className="flex items-center gap-2">
                  {Object.entries(topic.severity_distribution).map(
                    ([key, count]) =>
                      count > 0 ? (
                        <span
                          key={key}
                          className={`px-1.5 py-0.5 rounded text-[10px] ${SEVERITY_COLORS[key] || ""}`}
                        >
                          {SEVERITY_LABELS[key] || key}: {count}
                        </span>
                      ) : null
                  )}
                </div>
                <span>{topic.impact_percentage}%</span>
              </div>

              {topic.top_pattern && (
                <p className="mt-2 text-xs text-v2-muted-foreground italic leading-tight">
                  &ldquo;{topic.top_pattern.slice(0, 80)}&rdquo;
                </p>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  )
}
