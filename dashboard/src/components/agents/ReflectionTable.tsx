'use client'

import { useEffect, useState, useCallback } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { TableSkeleton } from '@/components/Skeleton'

export interface ReflectionInfo {
  agent: string
  task: string
  verdict: string
  confidence: number
  duration_ms: number
  error: string | null
  timestamp: string | null
}

function timeAgo(ts: string | null): string {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

const verdictBadge: Record<string, 'green' | 'red' | 'yellow'> = {
  success: 'green',
  failure: 'red',
  partial: 'yellow',
}

export default function ReflectionTable({ refreshKey }: { refreshKey: number }) {
  const [reflections, setReflections] = useState<ReflectionInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchReflections = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithAuth('/agents/reflections?limit=20')
      setReflections(data as ReflectionInfo[])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchReflections() }, [refreshKey, fetchReflections])

  if (loading) return <TableSkeleton rows={5} />
  if (error) return (
    <div className="flex items-center gap-2 text-red-400 text-body">
      <span>Failed to load reflections</span>
      <Button variant="ghost" onClick={fetchReflections}>Retry</Button>
    </div>
  )

  return (
    <Card className="mt-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-heading text-foreground">Recent Executions</h2>
        <Button variant="ghost" onClick={fetchReflections}>Refresh</Button>
      </div>
      {reflections.length === 0 ? (
        <p className="text-body text-foreground-muted text-center py-8">
          No executions yet. Run a task above to see results here.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-body">
            <thead>
              <tr className="border-b border-border text-small text-foreground-muted">
                <th className="text-left py-2 pr-4">Agent</th>
                <th className="text-left py-2 pr-4">Task</th>
                <th className="text-left py-2 pr-4">Verdict</th>
                <th className="text-right py-2 pr-4">Confidence</th>
                <th className="text-right py-2 pr-4">Duration</th>
                <th className="text-right py-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {reflections.map((r, i) => (
                <tr key={i} className="border-b border-border/50 text-foreground">
                  <td className="py-2 pr-4 font-medium">{r.agent}</td>
                  <td className="py-2 pr-4 max-w-xs truncate text-foreground-muted" title={r.task}>
                    {r.task}
                  </td>
                  <td className="py-2 pr-4">
                    <Badge variant={verdictBadge[r.verdict] || 'yellow'}>{r.verdict}</Badge>
                  </td>
                  <td className="py-2 pr-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <div className="w-12 h-1.5 bg-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full"
                          style={{ width: `${Math.round(r.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs">{Math.round(r.confidence * 100)}%</span>
                    </div>
                  </td>
                  <td className="py-2 pr-4 text-right text-foreground-muted">{r.duration_ms}ms</td>
                  <td className="py-2 text-right text-foreground-muted text-small">{timeAgo(r.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
