'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useWorkspace } from './context'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { FileText, BookOpen, Search, Activity, Upload, AlertCircle, RefreshCw, Folder, Clock } from 'lucide-react'
import Link from 'next/link'

interface KnowledgeObject {
  id: string
  title: string
  content_type: string
  lifecycle_state: string
  created_at: string
  updated_at: string
}

interface Collection {
  id: string
  name: string
  description?: string
}

export default function WorkspaceDashboard() {
  const router = useRouter()
  const { activeWorkspace } = useWorkspace()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [assets, setAssets] = useState<KnowledgeObject[]>([])
  const [collections, setCollections] = useState<Collection[]>([])

  const fetchData = useCallback(async () => {
    if (!activeWorkspace) return
    setLoading(true)
    setError(null)
    try {
      const [assetList, collectionList] = await Promise.all([
        fetchWithAuth(`/api/v1/knowledge?workspace_id=${activeWorkspace.id}`),
        fetchWithAuth(`/api/v1/collections?workspace_id=${activeWorkspace.id}`),
      ])
      setAssets(assetList)
      setCollections(collectionList)
    } catch (err: any) {
      setError(err.message || 'Failed to load workspace details')
    } finally {
      setLoading(false)
    }
  }, [activeWorkspace])

  useEffect(() => {
    fetchData()
    
    // Listen for workspace changed event
    window.addEventListener('workspaceChanged', fetchData)
    return () => {
      window.removeEventListener('workspaceChanged', fetchData)
    }
  }, [activeWorkspace])

  const totalAssets = assets.length
  const processingAssets = assets.filter(a => ['uploaded', 'processing'].includes(a.lifecycle_state.toLowerCase())).length
  const publishedAssets = assets.filter(a => ['published', 'active'].includes(a.lifecycle_state.toLowerCase())).length

  return (
    <DashboardLayout breadcrumbs={[{ label: 'Workspace', href: '/workspace' }, { label: 'Dashboard' }]}>
      <div className="flex flex-col gap-6">
        {/* Title / Description */}
        <div>
          <h1 className="verge-display text-4xl text-v2-text-primary leading-none">Workspace Dashboard</h1>
          <p className="text-sm text-v2-text-secondary mt-1">
            Manage files, custom curriculum documents, collections, and search indexes in this workspace.
          </p>
        </div>

        {/* Error State */}
        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div className="flex-1">{error}</div>
            <button onClick={fetchData} className="p-1 hover:bg-v2-error/15 rounded-lg">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Stats Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-v2-surface border border-v2-border p-5 rounded-[20px]">
            <p className="text-xs text-v2-text-secondary uppercase font-semibold">Total Assets</p>
            <p className="verge-display text-3xl text-v2-accent mt-1">{totalAssets}</p>
          </div>
          <div className="bg-v2-surface border border-v2-border p-5 rounded-[20px]">
            <p className="text-xs text-v2-text-secondary uppercase font-semibold">Active & Published</p>
            <p className="verge-display text-3xl text-v2-text-primary mt-1">{publishedAssets}</p>
          </div>
          <div className="bg-v2-surface border border-v2-border p-5 rounded-[20px]">
            <p className="text-xs text-v2-text-secondary uppercase font-semibold">Processing</p>
            <p className={`verge-display text-3xl mt-1 ${processingAssets > 0 ? 'text-v2-warning animate-pulse' : 'text-v2-text-secondary'}`}>
              {processingAssets}
            </p>
          </div>
          <div className="bg-v2-surface border border-v2-border p-5 rounded-[20px]">
            <p className="text-xs text-v2-text-secondary uppercase font-semibold">Collections</p>
            <p className="verge-display text-3xl text-v2-text-primary mt-1">{collections.length}</p>
          </div>
        </div>

        {/* Action Panel Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Link
            href="/workspace/upload"
            className="flex flex-col gap-3 p-6 bg-v2-surface border border-v2-border rounded-[20px] hover:border-v2-accent hover:-translate-y-0.5 transition-all group"
          >
            <div className="p-3 w-fit rounded-xl bg-v2-accentMuted text-v2-accent group-hover:bg-v2-accent group-hover:text-v2-bg transition-colors">
              <Upload className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-v2-text-primary mt-2">Upload Files</h3>
            <p className="text-xs text-v2-text-secondary">
              Ingest new textbooks, quizzes, lesson plans or school schedules into this workspace&rsquo;s knowledge pool.
            </p>
          </Link>

          <Link
            href="/workspace/browse"
            className="flex flex-col gap-3 p-6 bg-v2-surface border border-v2-border rounded-[20px] hover:border-v2-accent hover:-translate-y-0.5 transition-all group"
          >
            <div className="p-3 w-fit rounded-xl bg-v2-accentMuted text-v2-accent group-hover:bg-v2-accent group-hover:text-v2-bg transition-colors">
              <BookOpen className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-v2-text-primary mt-2">Browse Assets</h3>
            <p className="text-xs text-v2-text-secondary">
              Explore structural chapters, chunks, collection categories, and version histories of your workspace.
            </p>
          </Link>

          <Link
            href="/workspace/search"
            className="flex flex-col gap-3 p-6 bg-v2-surface border border-v2-border rounded-[20px] hover:border-v2-accent hover:-translate-y-0.5 transition-all group"
          >
            <div className="p-3 w-fit rounded-xl bg-v2-accentMuted text-v2-accent group-hover:bg-v2-accent group-hover:text-v2-bg transition-colors">
              <Search className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-v2-text-primary mt-2">Search Gateway</h3>
            <p className="text-xs text-v2-text-secondary">
              Perform deep semantic queries scoped to this workspace and review dynamic footnote citations.
            </p>
          </Link>

          <Link
            href="/workspace/processing"
            className="flex flex-col gap-3 p-6 bg-v2-surface border border-v2-border rounded-[20px] hover:border-v2-accent hover:-translate-y-0.5 transition-all group"
          >
            <div className="p-3 w-fit rounded-xl bg-v2-accentMuted text-v2-accent group-hover:bg-v2-accent group-hover:text-v2-bg transition-colors">
              <Activity className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-v2-text-primary mt-2">Processing Queue</h3>
            <p className="text-xs text-v2-text-secondary">
              Track active ingestion states (Parsing, Embedding, Indexing, and async educational Enrichment).
            </p>
          </Link>
        </div>

        {/* Bottom Section: Recent Files & Collections */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Files Table */}
          <div className="lg:col-span-2 bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-v2-border/40 pb-3">
              <h2 className="text-lg font-bold text-v2-text-primary">Recent Workspace Assets</h2>
              <Link href="/workspace/browse" className="text-xs text-v2-accent font-semibold hover:underline">
                View all
              </Link>
            </div>

            {loading ? (
              <div className="py-12 flex justify-center">
                <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" />
              </div>
            ) : assets.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-v2-border/30 text-xs text-v2-text-secondary uppercase">
                      <th className="py-2.5 font-semibold">Title</th>
                      <th className="py-2.5 font-semibold">State</th>
                      <th className="py-2.5 font-semibold">Uploaded</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-v2-border/20">
                    {assets.slice(0, 5).map(ko => (
                      <tr key={ko.id} className="text-sm hover:bg-v2-bg/30">
                        <td className="py-3 font-medium text-v2-text-primary flex items-center gap-2 max-w-xs sm:max-w-md truncate">
                          <FileText className="w-4 h-4 text-v2-text-secondary shrink-0" />
                          <span className="truncate">{ko.title}</span>
                        </td>
                        <td className="py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            ['published', 'active'].includes(ko.lifecycle_state.toLowerCase())
                              ? 'bg-v2-success/10 text-v2-success'
                              : ko.lifecycle_state.toLowerCase() === 'deleted'
                              ? 'bg-v2-error/10 text-v2-error'
                              : 'bg-v2-warning/10 text-v2-warning'
                          }`}>
                            {ko.lifecycle_state}
                          </span>
                        </td>
                        <td className="py-3 text-xs text-v2-text-secondary">
                          {new Date(ko.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-12 text-center text-sm text-v2-text-secondary">
                No files uploaded to this workspace yet.
              </div>
            )}
          </div>

          {/* Collections Panel */}
          <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4">
            <div className="flex items-center justify-between border-b border-v2-border/40 pb-3">
              <h2 className="text-lg font-bold text-v2-text-primary">Collections</h2>
            </div>

            {loading ? (
              <div className="py-12 flex justify-center">
                <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" />
              </div>
            ) : collections.length > 0 ? (
              <div className="flex flex-col gap-3">
                {collections.slice(0, 5).map(c => (
                  <div key={c.id} className="flex items-center gap-3 p-3 rounded-xl border border-v2-border bg-v2-bg/40">
                    <div className="p-2 bg-v2-accentMuted text-v2-accent rounded-lg border border-v2-accent/20">
                      <Folder className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-v2-text-primary truncate">{c.name}</p>
                      <p className="text-xs text-v2-text-secondary truncate">{c.description || 'No description'}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center text-sm text-v2-text-secondary">
                No collections created yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
