'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity, Plus, X, Loader2, AlertTriangle,
  Filter, CheckCircle, Clock,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId, isAuthenticated } from '@/lib/auth'
import { InterventionAnalytics } from '@/components/interventions/InterventionAnalytics'

export const dynamic = 'force-dynamic'

interface Intervention {
  id: string
  user_id: string
  intervention_type: string
  topic: string | null
  status: string
  priority: number
  estimated_impact: number
  effectiveness_score: number | null
  assigned_at: string
  started_at: string | null
  completed_at: string | null
}

export default function InterventionsPage() {
  const router = useRouter()
  const [items, setItems] = useState<Intervention[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  const fetchInterventions = async () => {
    setLoading(true)
    setError(null)
    try {
      let url = '/interventions'
      if (statusFilter) url += `?status=${statusFilter}`
      const data = await fetchWithAuth(url)
      setItems(Array.isArray(data) ? data : [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchInterventions()
  }, [statusFilter, router])

  const createFromReadiness = async () => {
    const userId = getUserId()
    if (!userId) return
    setCreating(true)
    setResult(null)
    try {
      await fetchWithAuth(`/interventions/from-readiness/${userId}`, {
        method: 'POST',
      }, 30000)
      setResult('✅ Interventions created from readiness analysis')
      setShowCreate(false)
      fetchInterventions()
    } catch (err: any) {
      setResult(`❌ ${err.message}`)
    } finally {
      setCreating(false)
    }
  }

  const statusColor = (s: string) => {
    switch (s) {
      case 'completed': return 'bg-green-500/10 text-green-400'
      case 'active': return 'bg-blue-500/10 text-blue-400'
      case 'cancelled': return 'bg-red-500/10 text-red-400'
      default: return 'bg-amber-500/10 text-amber-400'
    }
  }

  if (!isAuthenticated()) return null

  return (
    <DashboardLayout breadcrumbs={[
      { label: 'Overview', href: '/v2/overview' },
      { label: 'Interventions' },
    ]}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Interventions</h1>
          <p className="text-sm text-foreground-muted mt-1">Track, assign, and measure intervention effectiveness</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors"
          >
            <Plus className="w-4 h-4" /> From Readiness
          </button>
        </div>
      </div>

      {result && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm flex items-center justify-between ${
          result.startsWith('✅')
            ? 'bg-green-500/10 text-green-400 border border-green-500/20'
            : 'bg-red-500/10 text-red-400 border border-red-500/20'
        }`}>
          <span>{result}</span>
          <button onClick={() => setResult(null)} className="ml-3 hover:opacity-70"><X className="w-4 h-4" /></button>
        </div>
      )}

      <div className="mb-6">
        <InterventionAnalytics />
      </div>

      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">All Interventions</h2>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-foreground-muted" />
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border border-border rounded-lg text-sm bg-background-secondary text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All</option>
              <option value="planned">Planned</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12"><Loader2 className="w-6 h-6 animate-spin mx-auto text-foreground-muted" /></div>
        ) : error ? (
          <div className="text-center py-12"><AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" /><p className="text-red-400">{error}</p></div>
        ) : items.length === 0 ? (
          <div className="text-center py-16">
            <Activity className="w-12 h-12 text-border mx-auto mb-3" />
            <p className="text-foreground-muted font-medium">No interventions yet</p>
            <p className="text-sm text-foreground-muted/60 mt-1">Create interventions from readiness analysis</p>
          </div>
        ) : (
          <div className="overflow-hidden">
            <table className="w-full">
              <thead className="bg-background-secondary">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Topic</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Priority</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Effectiveness</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">Assigned</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.map(iv => (
                  <tr key={iv.id} className="hover:bg-background-secondary/50">
                    <td className="px-4 py-3 text-sm font-medium text-foreground">{iv.intervention_type.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-3 text-sm text-foreground-muted">{iv.topic || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(iv.status)}`}>
                        {iv.status === 'completed' ? <CheckCircle className="w-3 h-3" /> : iv.status === 'active' ? <Clock className="w-3 h-3" /> : null}
                        {iv.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground-muted">{(iv.priority * 100).toFixed(0)}%</td>
                    <td className="px-4 py-3 text-sm">
                      {iv.effectiveness_score !== null
                        ? <span className="text-green-400 font-medium">{iv.effectiveness_score.toFixed(1)}%</span>
                        : <span className="text-foreground-muted/50">—</span>
                      }
                    </td>
                    <td className="px-4 py-3 text-xs text-foreground-muted">{iv.assigned_at.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowCreate(false)}>
          <div className="bg-card border border-border rounded-xl shadow-xl p-6 w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-foreground">Create from Readiness</h2>
              <button onClick={() => setShowCreate(false)} className="text-foreground-muted hover:text-foreground"><X className="w-5 h-5" /></button>
            </div>
            <p className="text-sm text-foreground-muted mb-4">
              Generate intervention assignments from the current readiness analysis.
              This will create planned interventions for weak topics based on the
              InterventionPlanner recommendations.
            </p>
            <button
              onClick={createFromReadiness}
              disabled={creating}
              className="w-full py-3 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 flex items-center justify-center gap-2 transition-colors"
            >
              {creating ? <><Loader2 className="w-4 h-4 animate-spin" /> Creating...</> : 'Create Interventions'}
            </button>
          </div>
        </div>
      )}
    </DashboardLayout>
  )
}
