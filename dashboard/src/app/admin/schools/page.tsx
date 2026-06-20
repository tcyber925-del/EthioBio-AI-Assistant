'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'

export const dynamic = 'force-dynamic'

interface SchoolData {
  id: string
  name: string
  teacher_count?: number
  student_count?: number
  grade_range?: string
  created_at?: string
}

export default function AdminSchoolsPage() {
  const ts = useTranslations('admin.schools')
  const tc = useTranslations('common')
  const [schools, setSchools] = useState<SchoolData[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const data = await fetchWithAuth('/api/admin/schools')
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
      await fetchWithAuth('/api/teacher/schools', {
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

  if (error) return <p className="text-red-400">{tc('error')}: {error}</p>
  if (loading) return <p className="text-foreground-muted text-body">{tc('loading')}</p>

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-heading text-foreground">{ts('title')}</h1>
        <Button variant="primary" size="sm" onClick={() => setShowForm(true)}>
          + {ts('add_school')}
        </Button>
      </div>
      {showForm && (
        <Card className="mb-4">
          <div className="flex gap-2">
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={ts('school_name_placeholder')}
              className="flex-1 px-4 py-2 border border-border rounded-lg text-body bg-background text-foreground placeholder:text-foreground-muted/50 focus:outline-none focus:ring-2 focus:ring-primary"
              autoFocus
            />
            <Button variant="primary" size="md" onClick={create}>{tc('save')}</Button>
            <Button variant="secondary" size="md" onClick={() => setShowForm(false)}>{tc('cancel')}</Button>
          </div>
        </Card>
      )}
      <div className="grid gap-4">
        {schools.map((s: SchoolData) => (
          <Card key={s.id}>
            <h3 className="text-subhead text-foreground">{s.name}</h3>
            <p className="text-small text-foreground-muted mt-1">
              {ts('school_info', { teachers: s.teacher_count ?? '?', students: s.student_count ?? '?', grade: s.grade_range ?? 'N/A' })}
            </p>
          </Card>
        ))}
      </div>
    </div>
  )
}
