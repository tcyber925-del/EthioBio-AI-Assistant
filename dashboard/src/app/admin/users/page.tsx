'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { AlertTriangle, ChevronLeft, ChevronRight, RefreshCw, Search, Shield, UserCheck, Users } from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

const ROLES = ['all', 'student', 'teacher', 'parent', 'admin'] as const

interface UserData {
  id: string
  email: string | null
  role: string
  grade_level: number | null
  telegram_id: number | null
  is_active: boolean
  created_at: string
  children: Array<{ id: string; email: string }> | null
}

export default function AdminUsersPage() {
  const tu = useTranslations('admin.users')
  const tc = useTranslations('common')
  const [users, setUsers] = useState<UserData[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('all')
  const [error, setError] = useState<string | null>(null)
  const [updatingId, setUpdatingId] = useState<string | null>(null)
  const perPage = 20

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (role !== 'all') params.set('role', role)
      params.set('page', String(page))
      params.set('per_page', String(perPage))
      const data = await fetchWithAuth(`/api/admin/users?${params}`)
      setUsers(data.users || [])
      setTotal(data.total || 0)
    } catch (err: any) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, role])

  const handleSearch = () => { setPage(1); load() }

  const toggleStatus = async (userId: string, current: boolean) => {
    setUpdatingId(userId)
    try {
      await fetchWithAuth(`/api/admin/users/${userId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !current }),
      })
      load()
    } catch (err: any) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setUpdatingId(null)
    }
  }

  const changeRole = async (userId: string, newRole: string) => {
    setUpdatingId(userId)
    try {
      await fetchWithAuth(`/api/admin/users/${userId}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole }),
      })
      load()
    } catch (err: any) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setUpdatingId(null)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / perPage))

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Users className="w-6 h-6 text-primary" />
            {tu('title')}
          </h1>
          <p className="text-sm text-foreground-muted mt-1">{tu('users_subtitle', { count: total })}</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 px-4 py-2 text-sm border border-border rounded-lg hover:bg-card transition-colors text-foreground-muted hover:text-foreground">
          <RefreshCw className="w-4 h-4" /> {tc('refresh')}
        </button>
      </div>

      <div className="bg-card rounded-xl border border-border">
        <div className="p-4 border-b border-border flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-muted" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder={tu('search_placeholder_admin')}
              className="w-full pl-9 pr-3 py-2 bg-background border border-border rounded-lg text-sm text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:border-primary transition-colors"
            />
          </div>
          <div className="flex gap-1 flex-wrap">
            {ROLES.map(r => (
              <button
                key={r}
                onClick={() => { setRole(r); setPage(1) }}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  role === r
                    ? 'bg-primary/10 text-primary'
                    : 'text-foreground-muted hover:bg-background-secondary hover:text-foreground'
                }`}
              >
                {r === 'all' ? tu('all') : r.charAt(0).toUpperCase() + r.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 px-4 py-3 mx-4 mt-4 rounded-lg">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="p-8 text-center text-foreground-muted">{tc('loading_users')}...</div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center">
            <UserCheck className="w-10 h-10 text-border mx-auto mb-2" />
            <p className="text-foreground-muted font-medium">{tc('no_users_found')}</p>
            <p className="text-xs text-foreground-muted/60 mt-1">{tc('search_hint')}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-background-secondary">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tu('email')}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tu('role')}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tu('grade')}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tu('telegram')}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tu('children')}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tc('status')}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tc('created')}</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{tc('actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.map(u => (
                  <tr key={u.id} className="hover:bg-background-secondary/50 transition-colors">
                    <td className="px-4 py-3 text-sm text-foreground">{u.email ?? <span className="text-foreground-muted">—</span>}</td>
                    <td className="px-4 py-3">
                      <select
                        value={u.role}
                        onChange={e => changeRole(u.id, e.target.value)}
                        disabled={updatingId === u.id}
                        className={`px-2 py-1 rounded text-xs font-medium border transition-colors ${
                          u.role === 'admin' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' :
                          u.role === 'teacher' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                          u.role === 'student' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                          'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                        }`}
                      >
                        <option value="student">student</option>
                        <option value="teacher">teacher</option>
                        <option value="parent">parent</option>
                        <option value="admin">admin</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground-muted">{u.grade_level ?? '—'}</td>
                    <td className="px-4 py-3 text-sm font-mono text-foreground-muted text-xs">
                      {u.telegram_id ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      {u.children && u.children.length > 0 ? (
                        <div className="flex flex-col gap-0.5">
                          {u.children.map(c => (
                            <span key={c.id} className="text-xs text-foreground-muted truncate max-w-[120px] block">
                              {c.email}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-foreground-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        u.is_active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                      }`}>
                        {u.is_active ? tu('status_active') : tu('status_inactive')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground-muted">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => toggleStatus(u.id, u.is_active)}
                        disabled={updatingId === u.id}
                        className={`text-xs font-medium hover:underline disabled:opacity-50 ${
                          u.is_active ? 'text-red-400 hover:text-red-300' : 'text-green-400 hover:text-green-300'
                        }`}
                      >
                        {updatingId === u.id ? '...' : u.is_active ? tu('deactivate') : tu('activate')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="px-4 py-3 border-t border-border flex items-center justify-between text-sm">
          <span className="text-foreground-muted">
            {tu('page_of', { page, total: totalPages })}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border hover:bg-background-secondary transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-foreground-muted"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> {tu('previous')}
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-border hover:bg-background-secondary transition-colors disabled:opacity-30 disabled:cursor-not-allowed text-foreground-muted"
            >
              {tu('next')} <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
