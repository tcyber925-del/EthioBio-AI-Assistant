'use client'

import { useEffect, useState } from 'react'
import { useWorkspace } from '../context'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId } from '@/lib/auth'
import { FileText, Folder, Trash2, Download, Plus, AlertCircle, RefreshCw, FolderOpen, Calendar, ChevronRight, X } from 'lucide-react'

interface KnowledgeObject {
  id: string
  title: string
  content_type: string
  lifecycle_state: string
  created_at: string
  metadata: {
    storage_key?: string
    enrichment?: string
  }
}

interface Collection {
  id: string
  name: string
  description?: string
}

export default function BrowseAssetsPage() {
  const { activeWorkspace } = useWorkspace()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assets, setAssets] = useState<KnowledgeObject[]>([])
  const [collections, setCollections] = useState<Collection[]>([])
  
  // Filter States
  const [search, setSearch] = useState('')
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null)
  
  // Modal / Create Collection state
  const [showAddCollection, setShowAddCollection] = useState(false)
  const [newColName, setNewColName] = useState('')
  const [newColDesc, setNewColDesc] = useState('')
  const [creatingCollection, setCreatingCollection] = useState(false)

  const fetchData = async () => {
    if (!activeWorkspace) return
    setLoading(true)
    setError(null)
    try {
      const assetList = await fetchWithAuth(`/api/v1/knowledge/?workspace_id=${activeWorkspace.id}`)
      setAssets(assetList)

      const collectionList = await fetchWithAuth(`/api/v1/collections/?workspace_id=${activeWorkspace.id}`)
      setCollections(collectionList)
    } catch (err: any) {
      setError(err.message || 'Failed to load assets and collections')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()

    window.addEventListener('workspaceChanged', fetchData)
    return () => {
      window.removeEventListener('workspaceChanged', fetchData)
    }
  }, [activeWorkspace])

  const handleCreateCollection = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newColName.trim() || !activeWorkspace) return
    setCreatingCollection(true)
    try {
      const userId = getUserId() || 'system'
      await fetchWithAuth(`/api/v1/collections/?created_by=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: activeWorkspace.id,
          name: newColName,
          description: newColDesc,
        }),
      })
      setNewColName('')
      setNewColDesc('')
      setShowAddCollection(false)
      fetchData()
    } catch (err: any) {
      alert(err.message || 'Failed to create collection')
    } finally {
      setCreatingCollection(false)
    }
  }

  const handleDeleteAsset = async (id: string) => {
    if (!confirm('Are you sure you want to soft delete this knowledge object?')) return
    try {
      await fetchWithAuth(`/api/v1/knowledge/${id}`, { method: 'DELETE' })
      fetchData()
    } catch (err: any) {
      alert(err.message || 'Failed to delete asset')
    }
  }

  const handleDeleteCollection = async (id: string) => {
    if (!confirm('Are you sure you want to delete this collection?')) return
    try {
      await fetchWithAuth(`/api/v1/collections/${id}`, { method: 'DELETE' })
      fetchData()
    } catch (err: any) {
      alert(err.message || 'Failed to delete collection')
    }
  }

  const handleDownload = (id: string) => {
    const token = localStorage.getItem('ethiobio_token')
    const url = `/api/v1/knowledge/${id}/download${token ? `?token=${token}` : ''}`
    window.open(url, '_blank')
  }

  // Filter Logic
  const filteredAssets = assets.filter(asset => {
    const matchesSearch = asset.title.toLowerCase().includes(search.toLowerCase())
    // Add collection filtering logic if collection mapping information is present
    return matchesSearch
  })

  return (
    <DashboardLayout breadcrumbs={[{ label: 'Workspace', href: '/workspace' }, { label: 'Browse Assets' }]}>
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="verge-display text-4xl text-v2-text-primary leading-none">Browse Curriculum Assets</h1>
            <p className="text-sm text-v2-text-secondary mt-1">
              Explore your document collections, download materials, and manage lifecycle versions.
            </p>
          </div>
          <button
            onClick={() => setShowAddCollection(true)}
            className="inline-flex items-center justify-center gap-1.5 px-4 h-10 rounded-xl bg-v2-accent text-v2-inverted text-sm font-semibold hover:bg-white transition-colors self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" /> Create Collection
          </button>
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

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar Collections Selector */}
          <div className="lg:col-span-1 flex flex-col gap-4">
            <div className="bg-v2-surface border border-v2-border rounded-[20px] p-5 flex flex-col gap-3">
              <h3 className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold">Collections</h3>
              <div className="flex flex-col gap-1">
                <button
                  onClick={() => setSelectedCollection(null)}
                  className={`flex items-center justify-between p-2.5 rounded-xl text-sm font-medium transition-all ${
                    selectedCollection === null ? 'bg-v2-accentMuted text-v2-accent border border-v2-accent/20' : 'text-v2-text-secondary hover:text-v2-text-primary'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <FolderOpen className="w-4 h-4" /> All Assets
                  </span>
                  <span className="text-xs">{assets.length}</span>
                </button>

                {collections.map(col => (
                  <div key={col.id} className="group flex items-center justify-between p-1 rounded-xl">
                    <button
                      onClick={() => setSelectedCollection(col.id)}
                      className={`flex-1 flex items-center gap-2 p-1.5 rounded-lg text-sm text-left font-medium transition-all truncate ${
                        selectedCollection === col.id ? 'text-v2-accent font-semibold' : 'text-v2-text-secondary hover:text-v2-text-primary'
                      }`}
                    >
                      <Folder className="w-4 h-4 shrink-0" /> <span className="truncate">{col.name}</span>
                    </button>
                    <button
                      onClick={() => handleDeleteCollection(col.id)}
                      className="p-1 text-v2-text-secondary hover:text-v2-error opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Main Assets Browser */}
          <div className="lg:col-span-3 flex flex-col gap-4">
            {/* Search filter bar */}
            <div className="bg-v2-surface border border-v2-border rounded-[20px] p-4 flex gap-3">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search assets by title..."
                className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-2.5 flex-1 outline-none focus:border-v2-accent"
              />
            </div>

            {/* Assets Table */}
            <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6">
              {loading ? (
                <div className="py-20 flex justify-center">
                  <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" />
                </div>
              ) : filteredAssets.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-v2-border/30 text-xs text-v2-text-secondary uppercase">
                        <th className="py-3 font-semibold">Title</th>
                        <th className="py-3 font-semibold">State</th>
                        <th className="py-3 font-semibold">Uploaded</th>
                        <th className="py-3 font-semibold text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-v2-border/20">
                      {filteredAssets.map(ko => (
                        <tr key={ko.id} className="text-sm hover:bg-v2-bg/30">
                          <td className="py-4 font-medium text-v2-text-primary flex items-center gap-2 max-w-sm truncate">
                            <FileText className="w-4 h-4 text-v2-text-secondary shrink-0" />
                            <span className="truncate">{ko.title}</span>
                          </td>
                          <td className="py-4">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                              ['published', 'active'].includes(ko.lifecycle_state.toLowerCase())
                                ? 'bg-v2-success/10 text-v2-success'
                                : 'bg-v2-warning/10 text-v2-warning'
                            }`}>
                              {ko.lifecycle_state}
                            </span>
                          </td>
                          <td className="py-4 text-xs text-v2-text-secondary">
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3.5 h-3.5" />
                              {new Date(ko.created_at).toLocaleDateString()}
                            </span>
                          </td>
                          <td className="py-4 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleDownload(ko.id)}
                                title="Download File"
                                className="p-1.5 rounded-lg border border-v2-border hover:border-v2-accent text-v2-text-secondary hover:text-v2-accent transition-colors"
                              >
                                <Download className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => handleDeleteAsset(ko.id)}
                                title="Delete Asset"
                                className="p-1.5 rounded-lg border border-v2-border hover:border-v2-error text-v2-text-secondary hover:text-v2-error transition-colors"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-20 text-center">
                  <FolderOpen className="w-12 h-12 text-v2-text-secondary mx-auto mb-3" />
                  <p className="text-sm font-semibold text-v2-text-primary">No assets match your filters</p>
                  <p className="text-xs text-v2-text-secondary mt-1">
                    Try refining your search query or upload new curriculum assets.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Create Collection Dialog */}
      {showAddCollection && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-v2-surface border border-v2-border rounded-[20px] w-full max-w-md p-6 flex flex-col gap-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-v2-border/40 pb-2">
              <h3 className="text-lg font-bold text-v2-text-primary">Create New Collection</h3>
              <button onClick={() => setShowAddCollection(false)} className="p-1 text-v2-text-secondary hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateCollection} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">Collection Name</label>
                <input
                  type="text"
                  required
                  value={newColName}
                  onChange={(e) => setNewColName(e.target.value)}
                  placeholder="e.g. Unit 3 Resources"
                  className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-3 py-2 outline-none focus:border-v2-accent"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-v2-text-secondary uppercase font-semibold">Description</label>
                <textarea
                  value={newColDesc}
                  onChange={(e) => setNewColDesc(e.target.value)}
                  placeholder="Summarize what files are grouped here..."
                  rows={3}
                  className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-3 py-2 outline-none focus:border-v2-accent resize-none"
                />
              </div>
              <button
                type="submit"
                disabled={creatingCollection}
                className="h-10 rounded-xl bg-v2-accent text-v2-inverted text-sm font-bold hover:bg-white disabled:opacity-50 transition-colors flex items-center justify-center"
              >
                {creatingCollection ? 'Creating...' : 'Create Collection'}
              </button>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  )
}
