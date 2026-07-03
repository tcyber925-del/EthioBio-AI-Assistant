'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated, getUserRole, getUserId } from '@/lib/auth'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { DashboardSkeleton } from '@/components/dashboard-v2'
import { FolderKanban, Plus } from 'lucide-react'
import { WorkspaceContext, Workspace } from './context'

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [activeWorkspace, setActiveWorkspaceState] = useState<Workspace | null>(null)

  const fetchWorkspaces = async () => {
    try {
      const userId = getUserId()
      if (!userId) return
      const list = await fetchWithAuth(`/api/v1/workspaces/?user_id=${userId}`)
      setWorkspaces(list)
      
      const savedId = localStorage.getItem('ethiobio_active_workspace_id')
      const active = list.find((w: Workspace) => w.id === savedId) || list[0] || null
      if (active) {
        setActiveWorkspaceState(active)
        localStorage.setItem('ethiobio_active_workspace_id', active.id)
      }
    } catch (err) {
      console.error('Failed to fetch workspaces', err)
    }
  }

  const setActiveWorkspace = (ws: Workspace) => {
    setActiveWorkspaceState(ws)
    localStorage.setItem('ethiobio_active_workspace_id', ws.id)
    window.dispatchEvent(new Event('workspaceChanged'))
  }

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    const role = getUserRole()
    if (role !== 'admin' && role !== 'teacher') {
      router.push('/v2/overview')
      return
    }
    fetchWorkspaces().then(() => setReady(true))
  }, [router])

  if (!ready) return <DashboardSkeleton />

  return (
    <WorkspaceContext.Provider value={{ workspaces, activeWorkspace, setActiveWorkspace, refreshWorkspaces: fetchWorkspaces }}>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-v2-surface border border-v2-border p-4 rounded-[20px]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-v2-accentMuted text-v2-accent border border-v2-accent/30">
              <FolderKanban className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold">Active Workspace</p>
              {activeWorkspace ? (
                <p className="text-lg font-bold text-v2-text-primary">{activeWorkspace.name}</p>
              ) : (
                <p className="text-sm text-v2-text-secondary">No active workspace</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <select
              value={activeWorkspace?.id || ''}
              onChange={(e) => {
                const selected = workspaces.find(w => w.id === e.target.value)
                if (selected) setActiveWorkspace(selected)
              }}
              className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-3 py-2 w-full sm:w-48 outline-none focus:border-v2-accent"
            >
              {workspaces.map(w => (
                <option key={w.id} value={w.id} className="bg-v2-surface">
                  {w.name}
                </option>
              ))}
              {workspaces.length === 0 && <option value="">No workspaces found</option>}
            </select>
            <button
              onClick={() => router.push('/classroom')}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-v2-accent text-v2-inverted text-xs font-semibold hover:bg-white transition-colors"
            >
              <Plus className="w-4 h-4" /> Seed / Create
            </button>
          </div>
        </div>
        {children}
      </div>
    </WorkspaceContext.Provider>
  )
}
