'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { AlertTriangle, Plus, RefreshCw, School, Users, LogIn } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

interface Classroom {
  id: string
  name: string
  grade_level: number
  student_count: number
}

export default function ClassroomListPage() {
  const router = useRouter()
  const [classes, setClasses] = useState<Classroom[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newGrade, setNewGrade] = useState(9)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    loadClasses()
  }, [])

  const loadClasses = () => {
    setLoading(true)
    setError(null)
    fetchWithAuth('/teacher/classrooms')
      .then(d => setClasses(Array.isArray(d) ? d : []))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  const handleCreate = async () => {
    if (!newName) return
    try {
      await fetchWithAuth('/teacher/classrooms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName, grade_level: newGrade, student_ids: [] }),
      })
      setShowCreate(false)
      setNewName('')
      loadClasses()
    } catch (err: any) {
      setError(err.message)
    }
  }

  if (!isAuthenticated()) return null

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">My Classrooms</h1>
      </div>

      <button
        onClick={() => setShowCreate(!showCreate)}
        className="flex items-center gap-2 text-sm text-primary hover:underline mb-4"
      >
        <Plus className="w-4 h-4" /> {showCreate ? 'Cancel' : 'Create Classroom'}
      </button>

      {showCreate && (
        <div className="bg-card rounded-xl border border-border p-5 mb-6 space-y-3">
          <input
            type="text"
            placeholder="Classroom name"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            className="w-full text-sm bg-background border border-border rounded-lg px-3 py-2 text-foreground"
          />
          <div className="flex items-center gap-3">
            <label className="text-sm text-foreground-muted">Grade:</label>
            <select
              value={newGrade}
              onChange={e => setNewGrade(Number(e.target.value))}
              className="text-sm bg-background border border-border rounded-lg px-3 py-2 text-foreground"
            >
              {[9, 10, 11, 12].map(g => <option key={g} value={g}>{g}</option>)}
            </select>
            <button
              onClick={handleCreate}
              className="text-sm bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-hover transition-colors ml-auto"
            >
              Create
            </button>
          </div>
        </div>
      )}

      {loading && <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>}

      {error && (
        <div className="bg-card rounded-xl border border-border p-8 text-center">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-red-400">{error}</p>
          <button onClick={loadClasses} className="text-sm text-primary hover:underline mt-3 flex items-center gap-1 mx-auto">
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      )}

      {!loading && !error && classes.length === 0 && (
        <div className="bg-card rounded-xl border border-border p-8 text-center">
          <School className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">No classrooms yet</p>
          <p className="text-sm text-foreground-muted/60 mt-1">Create your first classroom to get started.</p>
        </div>
      )}

      {!loading && !error && classes.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {classes.map(c => (
            <Link
              key={c.id}
              href={`/classroom/${c.id}`}
              className="bg-card rounded-xl border border-border p-5 hover:border-primary/30 transition-colors block"
            >
              <h3 className="font-semibold text-foreground mb-1">{c.name}</h3>
              <p className="text-xs text-foreground-muted mb-3">Grade {c.grade_level}</p>
              <div className="flex items-center gap-2 text-sm text-foreground-muted">
                <Users className="w-4 h-4" />
                <span>{c.student_count} student{c.student_count !== 1 ? 's' : ''}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
