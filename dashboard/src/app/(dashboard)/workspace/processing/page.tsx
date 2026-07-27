'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { useWorkspace } from '../context'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { Activity, RefreshCw, AlertCircle, CheckCircle2, Clock, PlayCircle } from 'lucide-react'

interface KnowledgeObject {
  id: string
  title: string
  content_type: string
  lifecycle_state: string
  enrichment_status: string
  created_at: string
  metadata: {
    pipeline_stage?: string
    error?: string
  }
}

export default function ProcessingQueuePage() {
  const t = useTranslations('workspace')
  const { activeWorkspace } = useWorkspace()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assets, setAssets] = useState<KnowledgeObject[]>([])

  const fetchAssets = async () => {
    if (!activeWorkspace) return
    try {
      const response = await fetchWithAuth(`/api/v1/knowledge?workspace_id=${activeWorkspace.id}&limit=50`)
      const list = await response.json()
      setAssets(list)
      setError(null)
    } catch (err: any) {
      setError(err.message || t('processing_error'))
    } finally {
      setLoading(false)
    }
  }

  // Poll assets every 3 seconds if there is any asset in a non-terminal state
  useEffect(() => {
    fetchAssets()
    
    // Listen for workspace changed event
    window.addEventListener('workspaceChanged', fetchAssets)
    
    const interval = setInterval(() => {
      const hasPending = assets.some(a => 
        ['uploaded', 'processing'].includes(a.lifecycle_state.toLowerCase()) ||
        a.enrichment_status.toLowerCase() === 'pending'
      )
      if (hasPending) {
        fetchAssets()
      }
    }, 3000)

    return () => {
      window.removeEventListener('workspaceChanged', fetchAssets)
      clearInterval(interval)
    }
  }, [activeWorkspace, assets])

  const getProgressDetails = (state: string, enrichment: string) => {
    const s = state.toLowerCase()
    const e = enrichment.toLowerCase()
    if (s === 'failed') return { percent: 100, color: 'bg-v2-error', text: t('state_failed'), status: 'error' }
    if (s === 'uploaded') return { percent: 20, color: 'bg-v2-warning', text: t('state_uploaded'), status: 'pending' }
    if (s === 'processing') return { percent: 50, color: 'bg-v2-warning', text: t('state_processing'), status: 'pending' }
    if (s === 'published' && e === 'pending') return { percent: 80, color: 'bg-v2-accent', text: t('state_pending_enrichment'), status: 'pending' }
    if (s === 'published' || s === 'active') return { percent: 100, color: 'bg-v2-success', text: t('state_active'), status: 'success' }
    return { percent: 0, color: 'bg-v2-text-secondary', text: t('state_unknown'), status: 'unknown' }
  }

  return (
    <DashboardLayout breadcrumbs={[{ label: t('crumb_workspace'), href: '/workspace' }, { label: t('crumb_processing') }]}>
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="verge-display text-4xl text-v2-text-primary leading-none">{t('processing_title')}</h1>
            <p className="text-sm text-v2-text-secondary mt-1">
              {t('processing_subtitle')}
            </p>
          </div>
          <button
            onClick={fetchAssets}
            disabled={loading}
            className="p-2.5 bg-v2-surface border border-v2-border hover:border-v2-accent rounded-xl text-v2-text-primary disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Error State */}
        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {/* Ingestion Cards List */}
        {loading && assets.length === 0 ? (
          <div className="py-12 flex justify-center">
            <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" />
          </div>
        ) : assets.length > 0 ? (
          <div className="flex flex-col gap-4">
            {assets.map(ko => {
              const details = getProgressDetails(ko.lifecycle_state, ko.enrichment_status)
              return (
                <div key={ko.id} className="bg-v2-surface border border-v2-border rounded-[20px] p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  {/* Name and State */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-v2-text-primary truncate">{ko.title}</h3>
                      <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full font-semibold ${
                        details.status === 'success' ? 'bg-v2-success/10 text-v2-success' :
                        details.status === 'error' ? 'bg-v2-error/10 text-v2-error' : 'bg-v2-warning/10 text-v2-warning'
                      }`}>
                        {ko.lifecycle_state}
                      </span>
                    </div>
                    <p className="text-xs text-v2-text-secondary mt-1">
                      {t('details_line', { id: ko.id, type: ko.content_type.split('/')[1] || ko.content_type, date: new Date(ko.created_at).toLocaleString() })}
                    </p>

                    {ko.metadata.error && (
                      <p className="text-xs text-v2-error mt-2 bg-v2-error/10 p-2.5 rounded-xl border border-v2-error/20">
                        {t('error_prefix', { message: ko.metadata.error })}
                      </p>
                    )}
                  </div>

                  {/* Progress Indicator */}
                  <div className="flex flex-col gap-1.5 w-full md:w-64 shrink-0">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-v2-text-secondary font-medium truncate max-w-[180px]">
                        {details.text}
                      </span>
                      <span className="text-v2-text-primary font-bold">{details.percent}%</span>
                    </div>
                    <div className="w-full h-2 bg-v2-bg border border-v2-border rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-500 ${details.color}`}
                        style={{ width: `${details.percent}%` }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="bg-v2-surface border border-v2-border rounded-[20px] py-16 text-center">
            <Activity className="w-12 h-12 text-v2-text-secondary mx-auto mb-3" />
            <h3 className="text-lg font-bold text-v2-text-primary">{t('processing_empty_title')}</h3>
            <p className="text-sm text-v2-text-secondary mt-1 max-w-sm mx-auto">
              {t('processing_empty_hint')}
            </p>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
