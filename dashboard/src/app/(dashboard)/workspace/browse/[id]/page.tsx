'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useWorkspace } from '../../context'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { getUserId } from '@/lib/auth'
import {
  ArrowLeft, FileText, Download, AlertCircle, RefreshCw,
  BookOpen, Clock, Tag, Hash, FileType, Activity,
  Lightbulb, ListTree, ScrollText, Sparkles, FlaskConical,
  ChevronDown, Loader, Star,
} from 'lucide-react'

interface EnrichmentData {
  enriched: boolean
  excerpt?: string
  excerpt_source?: string
  key_terms?: string[]
  content_class?: string
  word_count?: number
  chunk_count?: number
}

interface KnowledgeDetail {
  id: string
  title: string
  content_type: string
  lifecycle_state: string
  enrichment_status: string
  version: number
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export default function KnowledgeDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string

  const [detail, setDetail] = useState<KnowledgeDetail | null>(null)
  const [enrichment, setEnrichment] = useState<EnrichmentData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showContent, setShowContent] = useState(false)
  const [content, setContent] = useState<string | null>(null)
  const [loadingContent, setLoadingContent] = useState(false)
  const [bookmarked, setBookmarked] = useState(false)
  const userId = getUserId()

  const checkBookmark = async () => {
    if (!userId) return
    try {
      const res = await fetchWithAuth(`/api/v1/bookmarks/check?ko_id=${id}&user_id=${userId}`)
      setBookmarked(res.bookmarked)
    } catch { /* ignore */ }
  }

  const toggleBookmark = async () => {
    if (!userId) return
    try {
      if (bookmarked) {
        await fetchWithAuth(`/api/v1/bookmarks/${id}?user_id=${userId}`, { method: 'DELETE' })
      } else {
        await fetchWithAuth(`/api/v1/bookmarks/${id}?user_id=${userId}`, { method: 'POST' })
      }
      setBookmarked(v => !v)
    } catch { /* ignore */ }
  }

  const fetchDetail = async () => {
    setLoading(true)
    setError(null)
    try {
      const [ko, enc] = await Promise.all([
        fetchWithAuth(`/api/v1/knowledge/${id}`),
        fetchWithAuth(`/api/v1/knowledge/${id}/enrichment`),
      ])
      setDetail(ko)
      setEnrichment(enc)
    } catch (err: any) {
      setError(err.message || 'Failed to load knowledge object')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchDetail(); checkBookmark() }, [id])

  const fetchContent = async () => {
    if (content) { setShowContent(v => !v); return }
    setLoadingContent(true)
    try {
      const res = await fetchWithAuth(`/api/v1/knowledge/${id}/content`)
      setContent(res.content || '')
      setShowContent(true)
    } catch {
      setContent('Failed to load content.')
    } finally {
      setLoadingContent(false)
    }
  }

  const handleDownload = () => {
    const token = localStorage.getItem('ethiobio_token')
    window.open(`/api/v1/knowledge/${id}/download${token ? `?token=${token}` : ''}`, '_blank')
  }

  const contentClassIcon = (cls: string | undefined) => {
    switch (cls) {
      case 'lesson': return <BookOpen className="w-4 h-4" />
      case 'assessment': return <ListTree className="w-4 h-4" />
      case 'lab_manual': return <FlaskConical className="w-4 h-4" />
      default: return <FileText className="w-4 h-4" />
    }
  }

  if (loading) {
    return (
      <DashboardLayout breadcrumbs={[{ label: 'Workspace', href: '/workspace' }, { label: 'Browse', href: '/workspace/browse' }, { label: 'Loading...' }]}>
        <div className="py-20 flex justify-center">
          <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin" />
        </div>
      </DashboardLayout>
    )
  }

  if (error || !detail) {
    return (
      <DashboardLayout breadcrumbs={[{ label: 'Workspace', href: '/workspace' }, { label: 'Browse', href: '/workspace/browse' }, { label: 'Error' }]}>
        <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <div className="flex-1">{error || 'Knowledge object not found'}</div>
          <button onClick={fetchDetail} className="p-1 hover:bg-v2-error/15 rounded-lg">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout breadcrumbs={[
      { label: 'Workspace', href: '/workspace' },
      { label: 'Browse', href: '/workspace/browse' },
      { label: detail.title },
    ]}>
      <div className="flex flex-col gap-6 max-w-4xl">
        {/* Back + Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              className="p-2 rounded-xl bg-v2-surface border border-v2-border hover:border-v2-accent text-v2-text-secondary hover:text-v2-accent transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div>
              <h1 className="verge-display text-3xl text-v2-text-primary leading-none truncate max-w-xl">{detail.title}</h1>
              <p className="text-sm text-v2-text-secondary mt-1 flex items-center gap-2">
                <FileType className="w-3.5 h-3.5" />
                {detail.content_type.replace(/^application\//, '')}
                <span className="text-v2-border/50">·</span>
                <Clock className="w-3.5 h-3.5" />
                {new Date(detail.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
            <button
              onClick={toggleBookmark}
              title={bookmarked ? 'Remove bookmark' : 'Bookmark'}
              className={`p-2.5 rounded-xl border transition-colors ${
                bookmarked
                  ? 'border-v2-warning/30 text-v2-warning bg-v2-warning/10'
                  : 'border-v2-border text-v2-text-secondary hover:border-v2-accent hover:text-v2-accent'
              }`}
            >
              <Star className={`w-5 h-5 ${bookmarked ? 'fill-v2-warning' : ''}`} />
            </button>
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 px-4 h-10 rounded-xl bg-v2-accent text-v2-inverted text-sm font-semibold hover:bg-white transition-colors"
            >
              <Download className="w-4 h-4" /> Download
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main — Enrichment / Excerpt */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            {/* Excerpt */}
            {enrichment?.excerpt && (
              <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6">
                <h2 className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold flex items-center gap-1.5 mb-3">
                  <ScrollText className="w-3.5 h-3.5" /> Excerpt
                </h2>
                <p className="text-sm text-v2-text-primary leading-relaxed">{enrichment.excerpt}</p>
                {enrichment.excerpt_source && (
                  <p className="text-xs text-v2-text-secondary mt-2">Source: {enrichment.excerpt_source.replace('_', ' ')}</p>
                )}
              </div>
            )}

            {/* Key Terms */}
            {enrichment?.key_terms && enrichment.key_terms.length > 0 && (
              <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6">
                <h2 className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold flex items-center gap-1.5 mb-3">
                  <Lightbulb className="w-3.5 h-3.5" /> Key Terms
                </h2>
                <div className="flex flex-wrap gap-2">
                  {enrichment.key_terms.map(term => (
                    <span key={term} className="text-xs px-2.5 py-1 rounded-full bg-v2-accent-muted text-v2-accent border border-v2-accent/20 font-medium">
                      {term}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* No enrichment */}
            {!enrichment?.enriched && (
              <div className="bg-v2-surface border border-v2-border rounded-[20px] p-6 text-center">
                <Sparkles className="w-8 h-8 text-v2-text-secondary mx-auto mb-2" />
                <p className="text-sm font-semibold text-v2-text-primary">Not yet enriched</p>
                <p className="text-xs text-v2-text-secondary mt-1">AI enrichment is pending for this asset.</p>
              </div>
            )}

            {/* Full Content Toggle */}
            <div className="bg-v2-surface border border-v2-border rounded-[20px] overflow-hidden">
              <button
                onClick={fetchContent}
                className="w-full flex items-center justify-between p-5 text-left hover:bg-v2-bg/30 transition-colors"
              >
                <h2 className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold flex items-center gap-1.5">
                  <ScrollText className="w-3.5 h-3.5" /> Full Content
                </h2>
                <ChevronDown className={`w-4 h-4 text-v2-text-secondary transition-transform duration-200 ${showContent ? 'rotate-180' : ''}`} />
              </button>
              {showContent && (
                <div className="px-5 pb-5">
                  {loadingContent ? (
                    <div className="flex items-center justify-center gap-2 py-8 text-sm text-v2-text-secondary">
                      <Loader className="w-4 h-4 animate-spin" /> Loading content...
                    </div>
                  ) : content ? (
                    <div className="max-h-[500px] overflow-y-auto bg-v2-bg border border-v2-border rounded-xl p-4">
                      <pre className="text-sm text-v2-text-primary leading-relaxed whitespace-pre-wrap font-sans">{content}</pre>
                    </div>
                  ) : (
                    <p className="text-sm text-v2-text-secondary text-center py-4">No content available.</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar — Metadata */}
          <div className="flex flex-col gap-4">
            <div className="bg-v2-surface border border-v2-border rounded-[20px] p-5 flex flex-col gap-4">
              <h3 className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold">Details</h3>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-v2-text-secondary flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5" /> State
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    ['published', 'active'].includes(detail.lifecycle_state)
                      ? 'bg-v2-success/10 text-v2-success'
                      : 'bg-v2-warning/10 text-v2-warning'
                  }`}>
                    {detail.lifecycle_state}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-v2-text-secondary flex items-center gap-1.5">
                    <Hash className="w-3.5 h-3.5" /> Version
                  </span>
                  <span className="text-sm font-mono text-v2-text-primary">v{detail.version}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-xs text-v2-text-secondary flex items-center gap-1.5">
                    <Tag className="w-3.5 h-3.5" /> Enrichment
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    detail.enrichment_status === 'complete' ? 'bg-v2-success/10 text-v2-success' :
                    detail.enrichment_status === 'failed' ? 'bg-v2-error/10 text-v2-error' :
                    'bg-v2-warning/10 text-v2-warning'
                  }`}>
                    {detail.enrichment_status}
                  </span>
                </div>

                {enrichment?.content_class && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-v2-text-secondary flex items-center gap-1.5">
                      {contentClassIcon(enrichment.content_class)} Class
                    </span>
                    <span className="text-xs font-medium text-v2-text-primary capitalize">{enrichment.content_class.replace('_', ' ')}</span>
                  </div>
                )}

                {enrichment?.word_count !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-v2-text-secondary flex items-center gap-1.5">
                      <FileText className="w-3.5 h-3.5" /> Words
                    </span>
                    <span className="text-sm font-mono text-v2-text-primary">{enrichment.word_count.toLocaleString()}</span>
                  </div>
                )}

                {enrichment?.chunk_count !== undefined && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-v2-text-secondary flex items-center gap-1.5">
                      <ListTree className="w-3.5 h-3.5" /> Chunks
                    </span>
                    <span className="text-sm font-mono text-v2-text-primary">{enrichment.chunk_count}</span>
                  </div>
                )}

                {detail.metadata?.chunk_count != null ? (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-v2-text-secondary flex items-center gap-1.5">
                      <ListTree className="w-3.5 h-3.5" /> Indexed Chunks
                    </span>
                    <span className="text-sm font-mono text-v2-text-primary">{String(detail.metadata.chunk_count)}</span>
                  </div>
                ) : null}
              </div>
            </div>

            {/* ID */}
            <div className="bg-v2-surface border border-v2-border rounded-[20px] p-5">
              <h3 className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold mb-2">Object ID</h3>
              <p className="text-xs font-mono text-v2-text-secondary break-all">{detail.id}</p>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
