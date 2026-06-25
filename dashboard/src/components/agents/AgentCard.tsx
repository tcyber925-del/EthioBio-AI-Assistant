'use client'

import Badge from '@/components/ui/Badge'
import Card from '@/components/ui/Card'

export interface AgentInfo {
  name: string
  description: string
  capabilities: string[]
  status: 'idle' | 'busy' | 'error'
  version: string
}

interface AgentCardProps {
  agent: AgentInfo
}

const statusBadge: Record<string, { variant: 'green' | 'yellow' | 'red'; label: string }> = {
  idle: { variant: 'green', label: 'Idle' },
  busy: { variant: 'yellow', label: 'Busy' },
  error: { variant: 'red', label: 'Error' },
}

const capabilityColors: Record<string, 'blue' | 'purple' | 'orange' | 'green' | 'red' | 'muted'> = {
  tutoring: 'blue',
  quiz_generation: 'purple',
  assessment_creation: 'purple',
  lesson_planning: 'orange',
  diagnostic_assessment: 'blue',
  translation: 'green',
  safety_review: 'red',
  diagram_generation: 'purple',
  student_progress: 'blue',
}

export default function AgentCard({ agent }: AgentCardProps) {
  const s = statusBadge[agent.status] || statusBadge.idle

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-subhead font-semibold text-foreground">{agent.name}</h3>
          <p className="text-small text-foreground-muted mt-0.5">{agent.description}</p>
        </div>
        <Badge variant={s.variant}>{s.label}</Badge>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {agent.capabilities.map(cap => (
          <Badge key={cap} variant={capabilityColors[cap] || 'muted'}>
            {cap.replace(/_/g, ' ')}
          </Badge>
        ))}
      </div>
      <div className="text-xs text-foreground-muted">v{agent.version}</div>
    </Card>
  )
}
