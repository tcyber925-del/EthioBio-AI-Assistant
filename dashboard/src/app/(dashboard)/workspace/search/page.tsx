'use client'

import { useState } from 'react'
import { useWorkspace } from '../context'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { Search, AlertCircle, RefreshCw, FileText, CheckCircle2, Bookmark } from 'lucide-react'

interface TextMatch {
  text: string
  chunk_index: number
  score: number
}

interface SearchResult {
  ko_id: string
  title: string
  content_type: string
  score: number
  matches: TextMatch[]
}

export default function SearchGatewayPage() {
  const { activeWorkspace } = useWorkspace()
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<SearchResult[]>([])

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || !activeWorkspace) return
    setSearching(true)
    setError(null)
    try {
      const list = await fetchWithAuth(
        `/api/v1/knowledge/search?q=${encodeURIComponent(query)}&workspace_id=${activeWorkspace.id}`
      )
      setResults(list)
    } catch (err: any) {
      setError(err.message || 'Search execution failed')
    } finally {
      setSearching(false)
    }
  }

  return (
    <DashboardLayout breadcrumbs={[{ label: 'Workspace', href: '/workspace' }, { label: 'Search Gateway' }]}>
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div>
          <h1 className="verge-display text-4xl text-v2-text-primary leading-none">Retrieval Search Gateway</h1>
          <p className="text-sm text-v2-text-secondary mt-1">
            Perform layer-scoped search queries against curriculum assets, textbooks, and notes in this workspace.
          </p>
        </div>

        {/* Search input bar */}
        <form onSubmit={handleSearch} className="bg-v2-surface border border-v2-border rounded-[20px] p-4 flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a learning topic or concept (e.g. cellular respiration)..."
            required
            disabled={searching}
            className="bg-v2-bg border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 flex-1 outline-none focus:border-v2-accent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={searching || !query.trim()}
            className="px-5 h-12 rounded-xl bg-v2-accent text-v2-inverted text-sm font-bold hover:bg-white disabled:opacity-50 transition-colors shrink-0 flex items-center gap-1.5"
          >
            {searching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Search
          </button>
        </form>

        {/* Error State */}
        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {/* Search Results Display */}
        {searching ? (
          <div className="py-20 flex justify-center">
            <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" />
          </div>
        ) : results.length > 0 ? (
          <div className="flex flex-col gap-6">
            <div className="text-xs text-v2-text-secondary uppercase font-semibold">
              Found {results.length} matching sources
            </div>
            
            <div className="flex flex-col gap-5">
              {results.map((r, idx) => (
                <div key={r.ko_id + idx} className="bg-v2-surface border border-v2-border rounded-[20px] p-6 flex flex-col gap-4">
                  {/* Source Metadata */}
                  <div className="flex items-center justify-between border-b border-v2-border/40 pb-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="p-2 rounded-lg bg-v2-accent-muted text-v2-accent border border-v2-accent/20 shrink-0">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-base font-bold text-v2-text-primary truncate">{r.title}</h3>
                        <p className="text-xs text-v2-text-secondary truncate">Asset ID: {r.ko_id}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-v2-text-secondary px-2 py-0.5 rounded-full border border-v2-border font-medium">
                        Relevance: {(r.score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  {/* Matching Excerpts */}
                  <div className="flex flex-col gap-3">
                    {r.matches.map((m, mIdx) => (
                      <div key={mIdx} className="bg-v2-bg/40 border border-v2-border/40 rounded-xl p-4 flex flex-col gap-2">
                        <div className="flex items-center justify-between text-xs text-v2-text-secondary">
                          <span className="flex items-center gap-1">
                            <Bookmark className="w-3.5 h-3.5" /> Chunk #{m.chunk_index}
                          </span>
                          <span>Score: {m.score.toFixed(3)}</span>
                        </div>
                        <p className="text-sm text-v2-text-primary leading-relaxed whitespace-pre-wrap italic">
                          &ldquo;{m.text}&rdquo;
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Structured Citation Badges */}
                  <div className="text-xs font-semibold uppercase text-v2-accent flex items-center gap-1 mt-1">
                    <span>Cited as:</span>
                    <span className="font-mono bg-v2-accent-muted px-2 py-0.5 rounded border border-v2-accent/20">
                      [{r.title} § Chunk {r.matches[0]?.chunk_index || 0}]
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : query ? (
          <div className="bg-v2-surface border border-v2-border rounded-[20px] py-16 text-center">
            <Search className="w-12 h-12 text-v2-text-secondary mx-auto mb-3" />
            <h3 className="text-lg font-bold text-v2-text-primary">No results found</h3>
            <p className="text-sm text-v2-text-secondary mt-1 max-w-xs mx-auto">
              Your search query didn&rsquo;t return any matching context within this workspace&rsquo;s indexed documents.
            </p>
          </div>
        ) : null}
      </div>
    </DashboardLayout>
  )
}
