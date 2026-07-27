'use client'

import { useTranslations } from 'next-intl'
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

const statusBadge: Record<string, { variant: 'green' | 'yellow' | 'red'; labelKey: string }> = {
  idle: { variant: 'green', labelKey: 'card_status_idle' },
  busy: { variant: 'yellow', labelKey: 'card_status_busy' },
  error: { variant: 'red', labelKey: 'card_status_error' },
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
  const t = useTranslations('agents')
  const s = statusBadge[agent.status] || statusBadge.idle

  const capabilityLabel = (cap: string) =>
    `capability_${cap}` in capabilityColors ? t(`capability_${cap}` as 'capability_tutoring') : cap.replace(/_/g, ' ')

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-subhead font-semibold text-foreground">{agent.name}</h3>
          <p className="text-small text-foreground-muted mt-0.5">{agent.description}</p>
        </div>
        <Badge variant={s.variant}>{t(s.labelKey as 'card_status_idle')}</Badge>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {agent.capabilities.map(cap => (
          <Badge key={cap} variant={capabilityColors[cap] || 'muted'}>
            {capabilityLabel(cap)}
          </Badge>
        ))}
      </div>
      <div className="text-xs text-foreground-muted">v{agent.version}</div>
    </Card>
  )
}
