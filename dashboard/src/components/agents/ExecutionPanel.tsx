'use client'

import { useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import type { AgentInfo } from './AgentCard'

interface ExecutionResult {
  task_id: string
  agent: string
  result: string | Record<string, unknown>
  confidence: number
  duration_ms: number
  error: string | null
}

interface ExecutionPanelProps {
  agents: AgentInfo[]
  onExecute: () => void
}

export default function ExecutionPanel({ agents, onExecute }: ExecutionPanelProps) {
  const [selectedAgent, setSelectedAgent] = useState('')
  const [task, setTask] = useState('')
  const [result, setResult] = useState<ExecutionResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleExecute = async () => {
    if (!selectedAgent || !task.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await fetchWithAuth('/agents/execute', {
        method: 'POST',
        body: JSON.stringify({ task: task.trim(), preferred_agent: selectedAgent }),
        headers: { 'Content-Type': 'application/json' },
      })
      setResult(data as ExecutionResult)
      onExecute()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="mt-6">
      <h2 className="text-heading text-foreground mb-4">Execute Task</h2>
      <div className="space-y-4">
        <div>
          <label htmlFor="agent-select" className="block text-small text-foreground-muted mb-1">Agent</label>
          <select
            value={selectedAgent}
            onChange={e => setSelectedAgent(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground text-body focus:outline-none focus:border-primary"
          >
            <option value="">Select an agent...</option>
            {agents.map(a => (
              <option key={a.name} value={a.name}>{a.name}</option>
            ))}
          </select>
        </div>
        <div>
            id="agent-select"
          <textarea
            value={task}
            onChange={e => setTask(e.target.value)}
            rows={3}
            placeholder="Describe the task for the agent..."
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground text-body focus:outline-none focus:border-primary resize-none"
          />
        </div>
        <Button
          variant="primary"
          onClick={handleExecute}
          loading={loading}
          disabled={!selectedAgent || !task.trim() || loading}
        >
          {loading ? 'Executing...' : 'Execute'}
        </Button>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-body">
            {error}
          </div>
        )}

        {result && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 space-y-2">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={result.error ? 'red' : 'green'}>
                {result.error ? 'Failed' : 'Success'}
              </Badge>
              <span className="text-small text-foreground-muted">
                {result.duration_ms}ms
              </span>
              {result.confidence > 0 && (
                <div className="flex items-center gap-1 ml-auto">
                  <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all"
                      style={{ width: `${Math.round(result.confidence * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-foreground-muted">
                    {Math.round(result.confidence * 100)}%
                  </span>
                </div>
              )}
            </div>
            <pre className="text-small text-foreground whitespace-pre-wrap font-mono bg-background rounded p-2 max-h-48 overflow-y-auto">
              {typeof result.result === 'string'
                ? result.result
                : JSON.stringify(result.result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </Card>
  )
}
