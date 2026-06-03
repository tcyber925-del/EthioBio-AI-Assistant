'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

const ROLES = ['all', 'student', 'teacher', 'parent', 'admin'] as const

export default function AdminUsersPage() {
  const [users, setUsers] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('all')
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (role !== 'all') params.set('role', role)
      const data = await fetchWithAuth(`/admin/users?${params}`)
      setUsers(data.users)
      setTotal(data.total)
    } catch (err: any) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [search, role])

  const toggleStatus = async (userId: string, current: boolean) => {
    await fetchWithAuth(`/admin/users/${userId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: !current }),
    })
    load()
  }

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (loading) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Users ({total})</h1>
      <div className="flex gap-4 mb-4">
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by email or telegram_id..." className="border rounded px-3 py-2 flex-1" />
        <div className="flex gap-2">
          {ROLES.map(r => (
            <button key={r} onClick={() => setRole(r)} className={`px-3 py-1 rounded text-sm ${role === r ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}>
              {r === 'all' ? 'All' : r.charAt(0).toUpperCase() + r.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-2 text-left">Email</th>
            <th className="p-2 text-left">Role</th>
            <th className="p-2 text-left">Grade</th>
            <th className="p-2 text-left">Telegram</th>
            <th className="p-2 text-left">Status</th>
            <th className="p-2 text-left">Created</th>
            <th className="p-2 text-left">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u: any) => (
            <tr key={u.id} className="border-t">
              <td className="p-2">{u.email ?? '-'}</td>
              <td className="p-2 capitalize">{u.role}</td>
              <td className="p-2">{u.grade_level ?? '-'}</td>
              <td className="p-2 font-mono text-xs">{u.telegram_id ?? '-'}</td>
              <td className="p-2">
                <span className={`px-2 py-0.5 rounded text-xs ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                  {u.is_active ? 'active' : 'inactive'}
                </span>
              </td>
              <td className="p-2 text-gray-500">{u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}</td>
              <td className="p-2">
                <button onClick={() => toggleStatus(u.id, u.is_active)} className={`text-xs hover:underline ${u.is_active ? 'text-red-600' : 'text-green-600'}`}>
                  {u.is_active ? 'Deactivate' : 'Activate'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
