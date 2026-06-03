'use client'

import { useEffect, useState } from 'react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

interface SchoolData {
  id: string
  name: string
  teacher_count?: number
  student_count?: number
  grade_range?: string
  created_at?: string
}

export default function AdminSchoolsPage() {
  const [schools, setSchools] = useState<SchoolData[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const data = await fetchWithAuth('/admin/schools')
      setSchools(data)
    } catch (err: any) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const create = async () => {
    if (!name.trim()) return
    setError(null)
    try {
      await fetchWithAuth('/teacher/schools', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() }),
      })
      setName('')
      setShowForm(false)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  if (error) return <p className="text-red-600">Error: {error}</p>
  if (loading) return <p className="text-gray-500">Loading...</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Schools</h1>
        <button onClick={() => setShowForm(true)} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          + Add School
        </button>
      </div>
      {showForm && (
        <div className="mb-4 flex gap-2">
          <input value={name} onChange={e => setName(e.target.value)} placeholder="School name" className="border rounded px-3 py-2 flex-1" autoFocus />
          <button onClick={create} className="bg-green-600 text-white px-4 py-2 rounded text-sm">Save</button>
          <button onClick={() => setShowForm(false)} className="text-gray-500 px-4 py-2 text-sm">Cancel</button>
        </div>
      )}
      <div className="grid gap-4">
        {schools.map((s: SchoolData) => (
          <div key={s.id} className="border rounded p-4 bg-white">
            <h3 className="font-semibold">{s.name}</h3>
            <p className="text-sm text-gray-500 mt-1">
              {s.teacher_count ?? '?'} teachers · {s.student_count ?? '?'} students · Grade {s.grade_range ?? 'N/A'}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
