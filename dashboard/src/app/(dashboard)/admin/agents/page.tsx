'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import PageHeader from '@/components/ui/PageHeader'
import { CardSkeleton } from '@/components/Skeleton'
import { Cpu, AlertTriangle, RefreshCw } from 'lucide-react'
import AgentCard from '@/components/agents/AgentCard'
import type { AgentInfo } from '@/components/agents/AgentCard'
import ExecutionPanel from '@/components/agents/ExecutionPanel'
import ReflectionTable from '@/components/agents/ReflectionTable'

export const dynamic = 'force-dynamic'

export default function AdminAgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const abortRef = useRef<AbortController | null>(null)

  const fetchAgents = useCallback(async () => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithAuth('/agents', { signal: controller.signal })
      setAgents(data as AgentInfo[])
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAgents() }, [fetchAgents])

  const handleExecute = () => {
    setRefreshKey(k => k + 1)
  }

  if (error && agents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <AlertTriangle className="w-12 h-12 text-red-400" />
        <p className="text-body text-red-400">{error}</p>
        <button
          onClick={fetchAgents}
          className="flex items-center gap-2 text-primary hover:underline text-subhead"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        icon={<Cpu className="w-6 h-6" />}
        title="Agent Orchestrator"
        description="Registered agents, task execution, and execution history"
      />

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : agents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 mt-6">
          <Cpu className="w-10 h-10 text-foreground-muted" />
          <p className="text-body text-foreground-muted">
            No agents registered. Check that the orchestrator is running.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {agents.map(agent => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      )}

      <ExecutionPanel agents={agents} onExecute={handleExecute} />

      <ReflectionTable refreshKey={refreshKey} />
    </div>
  )
}
