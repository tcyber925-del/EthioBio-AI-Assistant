'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchWithTimeout } from '@/lib/fetch'
import { getToken, isAuthenticated } from '@/lib/auth'

export interface HistoryTurn {
  id: string
  session_id: string | null
  role: string
  content: string
  topic: string | null
  created_at: string
}

export interface QAPair {
  question: HistoryTurn
  answer: HistoryTurn | null
  id: string
}

export interface DateGroup {
  label: string
  items: QAPair[]
}

function getDateLabel(date: Date): string {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diffDays = Math.floor((today.getTime() - target.getTime()) / 86400000)

  if (diffDays === 0) return 'today'
  if (diffDays === 1) return 'yesterday'
  if (diffDays < 7) return 'this_week'
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function pairTurns(data: HistoryTurn[]): QAPair[] {
  const pairs: QAPair[] = []
  const sorted = [...data].reverse()
  for (let i = 0; i < sorted.length; i++) {
    if (sorted[i].role === 'user' && i + 1 < sorted.length && sorted[i + 1].role === 'assistant') {
      pairs.push({ question: sorted[i], answer: sorted[i + 1], id: sorted[i].id })
    }
  }
  return pairs
}

function groupByDate(pairs: QAPair[]): DateGroup[] {
  const map = new Map<string, QAPair[]>()
  for (const pair of pairs) {
    const label = getDateLabel(new Date(pair.question.created_at))
    if (!map.has(label)) map.set(label, [])
    map.get(label)!.push(pair)
  }
  const order = ['today', 'yesterday', 'this_week']
  const groups: DateGroup[] = []
  for (const key of order) {
    if (map.has(key)) groups.push({ label: key, items: map.get(key)! })
  }
  map.forEach((items, key) => {
    if (!order.includes(key)) groups.push({ label: key, items })
  })
  return groups
}

interface UseConversationHistoryReturn {
  history: QAPair[]
  dateGroups: DateGroup[]
  loading: boolean
  error: boolean
  fetchHistory: () => Promise<void>
}

export function useConversationHistory(limit = 50): UseConversationHistoryReturn {
  const [history, setHistory] = useState<QAPair[]>([])
  const [dateGroups, setDateGroups] = useState<DateGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const reqId = useRef(0)

  const fetchHistory = useCallback(async () => {
    if (!isAuthenticated()) return
    const id = ++reqId.current
    setLoading(true)
    setError(false)
    try {
      const token = getToken()
      const data: HistoryTurn[] = await fetchWithTimeout(`/api/v1/memory/conversations?limit=${limit}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (id !== reqId.current) return
      const pairs = pairTurns(data)
      if (id !== reqId.current) return
      setHistory(pairs)
      setDateGroups(groupByDate(pairs))
    } catch {
      if (id !== reqId.current) return
      setError(true)
    } finally {
      if (id === reqId.current) setLoading(false)
    }
  }, [limit])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  return { history, dateGroups, loading, error, fetchHistory }
}
