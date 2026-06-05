'use client'

import { useState, useEffect } from 'react'
import { useTranslations } from 'next-intl'
import { Loader2, RefreshCw } from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'

interface ModelInfo {
  id: string
  name: string
  provider: string
  is_default: boolean
}

interface ModelSelectorProps {
  value: string
  onChange: (model: string) => void
  disabled?: boolean
}

export default function ModelSelector({ value, onChange, disabled }: ModelSelectorProps) {
  const tc = useTranslations('common')
  const [models, setModels] = useState<ModelInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadModels = async () => {
    try {
      const data = await fetchWithTimeout('/models')
      setModels(data)
      if (!value && data.length > 0) {
        const def = data.find((m: ModelInfo) => m.is_default) || data[0]
        onChange(def.id)
      }
    } catch (e) {
      console.error('Failed to load models:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadModels() }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await fetchWithTimeout('/models/refresh', { method: 'POST' })
      await loadModels()
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) return <div className="flex items-center gap-2 text-sm text-foreground-muted"><Loader2 className="w-4 h-4 animate-spin" />{tc('models_loading')}</div>

  return (
    <div className="flex items-center gap-2">
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={disabled}
        className="px-3 py-2 border border-border rounded-lg text-sm bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
      >
        {models.map(m => (
          <option key={m.id} value={m.id}>
            {m.name} ({m.provider}){m.is_default ? ' ★' : ''}
          </option>
        ))}
      </select>
      <button
        onClick={handleRefresh}
        disabled={refreshing}
        className="p-2 border border-border rounded-lg hover:bg-card transition-colors disabled:opacity-50"
        title={tc('refresh_models')}
      >
        <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
      </button>
    </div>
  )
}
