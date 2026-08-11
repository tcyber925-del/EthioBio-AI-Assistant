'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { ArrowLeft, BarChart3 } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { ErrorState } from '@/components/ui/errors'
import { fetchWithTimeout } from '@/lib/fetch'
import { isAuthenticated } from '@/lib/auth'
import { normalizeException, type AppError } from '@/lib/errors'
import ContinueLearningFeed from '@/components/learning/ContinueLearningFeed'
import GamificationProfile from '@/components/gamification/GamificationProfile'
import ActivityFeed from '@/components/ActivityFeed'
import ExamReadinessCard from '@/components/learning/ExamReadinessCard'

export const dynamic = 'force-dynamic'

export default function StudentDetailPage() {
  const params = useParams()
  const router = useRouter()
  const ts = useTranslations('student.dashboard')
  const tc = useTranslations('common')
  const [student, setStudent] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)

  const fetchStudent = async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await fetchWithTimeout(`/progress/student/${params.id}`)
      setStudent(d)
    } catch (err) {
      setError(normalizeException(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchStudent()
  }, [params.id, router])

  if (loading) return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  if (error) return (
    <div>
      <Link href="/students" className="flex items-center gap-2 text-sm text-foreground-muted hover:text-foreground mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" /> {ts('back_to_students')}
      </Link>
      <ErrorState
        error={error}
        title={tc('students_load_error')}
        onRetry={() => void fetchStudent()}
      />
    </div>
  )
  if (!student) return null

  return (
    <div>
      <Link href="/students" className="flex items-center gap-2 text-sm text-foreground-muted hover:text-foreground mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" /> {ts('back_to_students')}
      </Link>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">{ts('student_label', { id: student.id?.slice(0, 8) })}</h1>
        <p className="text-sm text-foreground-muted mt-1">{ts('grade_with_level', { grade: student.grade_level || 'N/A' })} · {student.language_preference}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-card rounded-xl border border-border p-5">
              <p className="text-sm text-foreground-muted">{ts('quiz_attempts')}</p>
              <p className="text-2xl font-bold text-foreground">{student.quiz_attempts || 0}</p>
            </div>
            <div className="bg-card rounded-xl border border-border p-5">
              <p className="text-sm text-foreground-muted">{ts('average_score')}</p>
              <p className="text-2xl font-bold text-foreground">{student.avg_score ? `${Math.round(student.avg_score)}%` : '—'}</p>
            </div>
            <div className="bg-card rounded-xl border border-border p-5">
              <p className="text-sm text-foreground-muted">{ts('weak_areas')}</p>
              <p className="text-2xl font-bold text-foreground">{student.weak_areas?.length || 0}</p>
            </div>
          </div>

          {student.weak_areas && student.weak_areas.length > 0 && (
            <div className="bg-card rounded-xl border border-border p-5">
              <h2 className="text-lg font-semibold text-foreground mb-3">{ts('weak_areas')}</h2>
              <div className="flex flex-wrap gap-2">
                {student.weak_areas.map((area: string, i: number) => (
                  <span key={i} className="px-3 py-1 bg-red-500/10 text-red-400 rounded-full text-sm">{area}</span>
                ))}
              </div>
            </div>
          )}

          {!student.quiz_attempts && (
            <div className="bg-card rounded-xl border border-border p-8 text-center">
              <BarChart3 className="w-12 h-12 text-border mx-auto mb-3" />
              <p className="text-foreground-muted font-medium">{ts('no_quiz_data')}</p>
              <p className="text-sm text-foreground-muted/60 mt-1">{ts('no_quiz_data_desc')}</p>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <ContinueLearningFeed userId={params.id as string} />
          <ExamReadinessCard userId={params.id as string} />
          <ContinueLearningFeed userId={params.id as string} />
          <GamificationProfile userId={params.id as string} />
          <ActivityFeed userId={params.id as string} />
        </div>
      </div>
    </div>
  )
}
