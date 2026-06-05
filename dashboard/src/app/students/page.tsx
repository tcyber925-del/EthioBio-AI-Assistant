'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { Users, AlertTriangle, RefreshCw } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface Student {
  id: string; telegram_id: number | null
  role: string; language_preference: string
  grade_level: number | null; created_at: string
}

export default function StudentsPage() {
  const router = useRouter()
  const locale = useLocale()
  const t = useTranslations('common')
  const [students, setStudents] = useState<Student[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStudents = async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await fetchWithAuth('/api/admin/dashboard')
      setStudents(d.recent_users || [])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchStudents()
  }, [router])

  if (loading) return <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  if (error) return (
    <div className="text-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-red-400">{error}</p>
      <button onClick={fetchStudents} className="mt-4 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
        <RefreshCw className="w-4 h-4 inline mr-1" /> {t('retry')}
      </button>
    </div>
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('students')}</h1>
          <p className="text-sm text-foreground-muted mt-1">{t('students_subtitle')}</p>
        </div>
      </div>

      {students.length === 0 ? (
        <div className="bg-card rounded-xl border border-border p-8 text-center">
          <Users className="w-12 h-12 text-border mx-auto mb-3" />
          <p className="text-foreground-muted font-medium">{t('no_students')}</p>
          <p className="text-sm text-foreground-muted/60 mt-1">{t('no_students_desc')}</p>
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-border">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-background-secondary">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('telegram_id')}</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('role')}</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('language')}</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('grade')}</th>
                  <th className="px-5 py-3 text-left text-xs font-medium text-foreground-muted uppercase">{t('joined')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                  {students.map((s: any) => (
                  <tr key={s.id} onClick={() => router.push(`/students/${s.id}`)} className="hover:bg-background-secondary/50 cursor-pointer">
                    <td className="px-5 py-3 text-sm text-foreground font-mono text-xs">{s.telegram_id || '—'}</td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        s.role === 'teacher' ? 'bg-blue-500/10 text-blue-400' :
                        s.role === 'admin' ? 'bg-purple-500/10 text-purple-400' :
                        'bg-green-500/10 text-green-400'
                      }`}>
                        {s.role}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-sm text-foreground-muted capitalize">{s.language_preference}</td>
                    <td className="px-5 py-3 text-sm text-foreground-muted">{s.grade_level ? `${t('grade')} ${s.grade_level}` : '—'}</td>
                    <td className="px-5 py-3 text-sm text-foreground-muted">{new Date(s.created_at).toLocaleDateString(locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
