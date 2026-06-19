'use client'

import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Check,
  Image,
  Layers,
  Loader2,
  Search,
  X,
} from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'

interface IconCategory {
  name: string
  icon_count: number
}

interface IconEntry {
  id: string
  name: string
  category: string
  author: string
  license: string
  grade_tags: number[]
}

interface IconListResponse {
  total: number
  icons: IconEntry[]
  categories: IconCategory[]
}

interface IconComposeResponse {
  diagram_svg: string
  title: string
  topic: string
  placed_icons: number
}

interface IconPaletteProps {
  onComposedSvg: (svg: string, title: string) => void
}

export default function IconPalette({ onComposedSvg }: IconPaletteProps) {
  const [categories, setCategories] = useState<IconCategory[]>([])
  const [icons, setIcons] = useState<IconEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [composing, setComposing] = useState(false)
  const [topic, setTopic] = useState('')
  const canvasRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchCategories()
  }, [])

  useEffect(() => {
    fetchIcons()
  }, [selectedCategory])

  const fetchCategories = async () => {
    try {
      const data: IconListResponse = await fetchWithTimeout('/diagram/icons?limit=1', {
        method: 'GET',
      })
      setCategories(data.categories)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const fetchIcons = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ limit: '200' })
      if (selectedCategory && selectedCategory !== 'All_icons') {
        params.set('category', selectedCategory)
      }
      const data: IconListResponse = await fetchWithTimeout(
        `/diagram/icons?${params}`,
        { method: 'GET' },
      )
      setIcons(data.icons)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams({ limit: '200' })
      if (search.trim()) params.set('search', search.trim())
      if (selectedCategory && selectedCategory !== 'All_icons') {
        params.set('category', selectedCategory)
      }
      const data: IconListResponse = await fetchWithTimeout(
        `/diagram/icons?${params}`,
        { method: 'GET' },
      )
      setIcons(data.icons)
      setTotal(data.total)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const toggleIcon = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const composeDiagram = async () => {
    if (selectedIds.size === 0) return
    setComposing(true)
    try {
      const data: IconComposeResponse = await fetchWithTimeout('/diagram/compose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic || 'Biology Diagram',
          icon_ids: Array.from(selectedIds),
          title: topic || 'Biology Diagram',
        }),
      })
      onComposedSvg(data.diagram_svg, data.title)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setComposing(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <select
          value={selectedCategory}
          onChange={e => setSelectedCategory(e.target.value)}
          className="flex-1 px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat.name} value={cat.name}>
              {cat.name.replace(/_/g, ' ')} ({cat.icon_count})
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="Search icons..."
            className="px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary w-48"
          />
          <button
            onClick={handleSearch}
            className="px-3 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors"
          >
            <Search className="w-4 h-4" />
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary mx-auto" />
          <p className="text-sm text-foreground-muted mt-2">Loading icons...</p>
        </div>
      )}

      {!loading && icons.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-foreground-muted">
              {total} icon{total !== 1 ? 's' : ''}
              {selectedIds.size > 0 && (
                <span className="ml-2 text-primary">
                  ({selectedIds.size} selected)
                </span>
              )}
            </p>
          </div>
          <div className="grid grid-cols-8 gap-2 max-h-96 overflow-y-auto">
            {icons.map(icon => {
              const selected = selectedIds.has(icon.id)
              return (
                <button
                  key={icon.id}
                  onClick={() => toggleIcon(icon.id)}
                  className={`relative flex flex-col items-center gap-1 p-2 rounded-lg border text-xs transition-all ${
                    selected
                      ? 'border-primary bg-primary/10 ring-1 ring-primary'
                      : 'border-border hover:bg-background-secondary'
                  }`}
                  title={icon.name}
                >
                  <Image className="w-6 h-6 text-foreground-muted" />
                  <span className="text-[10px] text-foreground-muted text-center leading-tight truncate w-full">
                    {icon.name}
                  </span>
                  {selected && (
                    <div className="absolute top-1 right-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
                      <Check className="w-3 h-3 text-white" />
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </>
      )}

      {!loading && icons.length === 0 && !error && (
        <div className="text-center py-8">
          <Layers className="w-8 h-8 text-border mx-auto mb-2" />
          <p className="text-sm text-foreground-muted">No icons found</p>
        </div>
      )}

      <div className="flex items-center gap-3 pt-3 border-t border-border">
        <input
          type="text"
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="Diagram title..."
          className="flex-1 px-3 py-2 border border-border rounded-lg text-sm bg-background text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <button
          onClick={composeDiagram}
          disabled={selectedIds.size === 0 || composing}
          className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
        >
          {composing ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Composing...</>
          ) : (
            <><Layers className="w-4 h-4" /> Compose Diagram ({selectedIds.size})</>
          )}
        </button>
      </div>
    </div>
  )
}
