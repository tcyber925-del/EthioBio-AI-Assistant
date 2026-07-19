'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Clock, Loader2, MessageSquare, Search, RefreshCw, AlertCircle } from 'lucide-react'
import type { DateGroup, QAPair } from '@/hooks/useConversationHistory'

interface ConversationSidebarProps {
  dateGroups: DateGroup[]
  loading: boolean
  error: boolean
  activeId: string | null
  onSelect: (pair: QAPair) => void
  onRefresh: () => void
}

export function ConversationSidebar({
  dateGroups,
  loading,
  error,
  activeId,
  onSelect,
  onRefresh,
}: ConversationSidebarProps) {
  const ta = useTranslations('ask')
  const [query, setQuery] = useState('')

  const filtered = query.trim()
    ? dateGroups.map(g => ({
        ...g,
        items: g.items.filter(i => i.question.content.toLowerCase().includes(query.toLowerCase())),
      })).filter(g => g.items.length > 0)
    : dateGroups

  return (
    <aside className="lg:col-span-1">
      <div className="rounded-[20px] border border-v2-border bg-v2-bg p-4 h-full flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <h3 className="verge-label text-v2-text-secondary">{ta('recent_questions')}</h3>
          <button
            onClick={onRefresh}
            disabled={loading}
            className="text-v2-text-muted hover:text-v2-text-secondary transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="relative mb-3">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-v2-text-muted" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={ta('search_history')}
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-v2-surface border border-v2-border rounded-lg text-v2-text-primary placeholder:text-v2-text-muted/50 focus:outline-none focus:ring-1 focus:ring-v2-accent"
          />
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 min-h-0 scrollbar-thin">
          {loading && (
            <div className="flex items-center gap-2 text-xs text-v2-text-muted py-4">
              <Loader2 className="w-3 h-3 animate-spin" />
              {ta('loading_history')}
            </div>
          )}

          {!loading && error && (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <p className="text-xs text-red-400">{ta('load_history_error')}</p>
              <button onClick={onRefresh} className="text-xs text-v2-accent hover:underline">
                {ta('retry')}
              </button>
            </div>
          )}

          {!loading && !error && filtered.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <MessageSquare className="w-5 h-5 text-v2-text-muted/40" />
              <p className="text-xs text-v2-text-muted">{query ? ta('no_search_results') : ta('no_history')}</p>
            </div>
          )}

          {!loading && !error && filtered.map(group => (
            <div key={group.label}>
              <h4 className="verge-label text-[10px] text-v2-text-muted mb-1.5 px-1">{ta(group.label)}</h4>
              <div className="space-y-1">
                {group.items.map(pair => (
                  <button
                    key={pair.id}
                    onClick={() => onSelect(pair)}
                    className={`w-full text-left p-2.5 rounded-xl border transition-colors ${
                      activeId === pair.id
                        ? 'border-v2-accent bg-v2-accent/5'
                        : 'border-transparent hover:border-v2-border hover:bg-v2-surface'
                    }`}
                  >
                    <p className="text-xs font-medium text-v2-text-primary line-clamp-1 leading-snug">
                      {pair.question.content}
                    </p>
                    {pair.answer && (
                      <p className="text-[11px] text-v2-text-muted mt-0.5 line-clamp-1 leading-snug">
                        {pair.answer.content}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}
