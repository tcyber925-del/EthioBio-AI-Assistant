'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import {
  AlertTriangle,
  BarChart3,
  RefreshCw,
  School,
  Shield,
  TrendingUp,
  Users,
} from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

interface SchoolItem {
  id: string
  name: string
}

interface TeacherMetric {
  teacher_id: string
  classroom_count: number
  avg_student_readiness: number
  intervention_rate: number
  active_plan_count: number
}

interface SchoolProfile {
  school_id: string
  total_teachers: number
  total_classrooms: number
  total_students: number
  avg_health: number
  health_distribution: Record<string, number>
  teacher_metrics: TeacherMetric[]
  at_risk_classrooms: { class_id: string; name: string; health: number; risk_student_count: number }[]
}

interface TrendPoint {
  snapshot_date: string
  avg_health: number
  total_students: number
  at_risk_count: number
}

function healthColor(score: number): string {
  if (score >= 80) return 'text-green-400'
  if (score >= 60) return 'text-emerald-400'
  if (score >= 40) return 'text-yellow-400'
  return 'text-red-400'
}

function healthBg(score: number): string {
  if (score >= 80) return 'bg-green-500/10 border-green-500/20'
  if (score >= 60) return 'bg-emerald-500/10 border-emerald-500/20'
  if (score >= 40) return 'bg-yellow-500/10 border-yellow-500/20'
  return 'bg-red-500/10 border-red-500/20'
}

export default function SchoolDashboardPage() {
  const router = useRouter()
  const locale = useLocale()
  const ts = useTranslations('admin.schools')
  const tc = useTranslations('common')
  const [schools, setSchools] = useState<SchoolItem[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [profile, setProfile] = useState<SchoolProfile | null>(null)
  const [trends, setTrends] = useState<TrendPoint[]>([])
  const [loadingSchools, setLoadingSchools] = useState(true)
  const [loadingProfile, setLoadingProfile] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/login')
      return
    }
    fetchWithAuth('/teacher/schools')
      .then(setSchools)
      .catch(err => setError(err.message))
      .finally(() => setLoadingSchools(false))
  }, [])

  const loadSchool = useCallback((schoolId: string) => {
    setLoadingProfile(true)
    setError(null)
    Promise.all([
      fetchWithAuth(`/teacher/schools/${schoolId}/overview`),
      fetchWithAuth(`/teacher/schools/${schoolId}/trends?days=30`),
    ])
      .then(([p, t]) => {
        setProfile(p)
        setTrends(t)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoadingProfile(false))
  }, [])

  useEffect(() => {
    if (selectedId) loadSchool(selectedId)
  }, [selectedId])

  if (loadingSchools) {
    return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <School className="w-6 h-6" />
            {ts('school_intelligence')}
          </h1>
          <p className="text-foreground-muted text-sm mt-1">{ts('school_intelligence_subtitle')}</p>
        </div>
        <select
          value={selectedId}
          onChange={e => setSelectedId(e.target.value)}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground"
        >
          <option value="">{ts('select_school')}</option>
          {schools.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="text-center py-8">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-red-400 text-sm">{error}</p>
          <button onClick={() => selectedId && loadSchool(selectedId)} className="text-sm text-primary hover:underline mt-2 flex items-center gap-1 mx-auto">
            <RefreshCw className="w-3 h-3" /> {tc('retry')}
          </button>
        </div>
      )}

      {loadingProfile && (
        <div className="space-y-4">{Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}</div>
      )}

      {!loadingProfile && !error && profile && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className={`rounded-xl border p-4 ${healthBg(profile.avg_health)}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">{ts('school_health')}</span>
                <Shield className={`w-4 h-4 ${healthColor(profile.avg_health)}`} />
              </div>
              <p className={`text-2xl font-bold ${healthColor(profile.avg_health)}`}>
                {profile.avg_health.toFixed(0)}
              </p>
              <p className="text-xs text-foreground-muted mt-1">
                {profile.total_students} students across {profile.total_classrooms} classrooms
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">{ts('teacher_count')}</span>
                <Users className="w-4 h-4 text-primary" />
              </div>
              <p className="text-2xl font-bold text-foreground">{profile.total_teachers}</p>
              <p className="text-xs text-foreground-muted mt-1">{ts('active_educators')}</p>
            </div>

            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">Classrooms</span>
                <BarChart3 className="w-4 h-4 text-blue-400" />
              </div>
              <p className="text-2xl font-bold text-foreground">{profile.total_classrooms}</p>
              <p className="text-xs text-foreground-muted mt-1">
                {profile.health_distribution.Critical + profile.health_distribution.Developing} at risk
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-foreground-muted font-medium">At-Risk Classrooms</span>
                <AlertTriangle className="w-4 h-4 text-red-400" />
              </div>
              <p className="text-2xl font-bold text-red-400">{profile.at_risk_classrooms.length}</p>
              <p className="text-xs text-foreground-muted mt-1">{ts('need_attention')}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="rounded-xl border border-border bg-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                {ts('health_trend')}
              </h3>
              {trends.length === 0 ? (
                <p className="text-xs text-foreground-muted py-4 text-center">{ts('no_trend_data')}</p>
              ) : (
                <div className="space-y-2">
                  {trends.map((t, i) => (
                    <div key={i} className="flex items-center gap-3 text-xs">
                      <span className="text-foreground-muted w-24 shrink-0">
                        {new Date(t.snapshot_date).toLocaleDateString(locale)}
                      </span>
                      <div className="flex-1 h-2 bg-background-secondary rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${t.avg_health >= 80 ? 'bg-green-400' : t.avg_health >= 60 ? 'bg-emerald-400' : t.avg_health >= 40 ? 'bg-yellow-400' : 'bg-red-400'}`}
                          style={{ width: `${t.avg_health}%` }}
                        />
                      </div>
                      <span className={`font-medium w-8 text-right ${healthColor(t.avg_health)}`}>
                        {t.avg_health.toFixed(0)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-3">
                <button
                  onClick={() => {
                    fetchWithAuth(`/teacher/schools/${selectedId}/snapshot`, { method: 'POST' })
                      .then(() => loadSchool(selectedId))
                  }}
                  className="text-xs text-primary hover:underline"
                >
                  {ts('take_snapshot')}
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card p-4">
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" />
                {ts('health_distribution')}
              </h3>
              <div className="space-y-3">
                {[
                  { label: 'Strong', count: profile.health_distribution.Strong, color: 'bg-green-400' },
                  { label: 'Ready', count: profile.health_distribution.Ready, color: 'bg-emerald-400' },
                  { label: 'Developing', count: profile.health_distribution.Developing, color: 'bg-yellow-400' },
                  { label: 'Critical', count: profile.health_distribution.Critical, color: 'bg-red-400' },
                ].map(band => {
                  const total = Object.values(profile.health_distribution).reduce((a, b) => a + b, 0)
                  const pct = total > 0 ? (band.count / total) * 100 : 0
                  return (
                    <div key={band.label} className="flex items-center gap-3 text-xs">
                      <span className="text-foreground-muted w-20">{band.label}</span>
                      <div className="flex-1 h-2 bg-background-secondary rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${band.color}`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-foreground font-medium w-6 text-right">{band.count}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-4 mb-6">
            <h3 className="text-sm font-semibold text-foreground mb-3">{ts('teacher_performance')}</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-foreground-muted text-xs border-b border-border">
                    <th className="pb-2 font-medium">{ts('teacher_id')}</th>
                    <th className="pb-2 font-medium">Classrooms</th>
                    <th className="pb-2 font-medium">{ts('avg_readiness')}</th>
                    <th className="pb-2 font-medium">{ts('intervention_rate')}</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.teacher_metrics.map(tm => (
                    <tr key={tm.teacher_id} className="border-b border-border/50 text-foreground">
                      <td className="py-2.5 font-mono text-xs text-foreground-muted">{tm.teacher_id.slice(0, 8)}...</td>
                      <td className="py-2.5">{tm.classroom_count}</td>
                      <td className="py-2.5">
                        <span className={healthColor(tm.avg_student_readiness)}>{tm.avg_student_readiness.toFixed(0)}</span>
                      </td>
                      <td className="py-2.5">{tm.intervention_rate.toFixed(1)}</td>
                    </tr>
                  ))}
                  {profile.teacher_metrics.length === 0 && (
                    <tr><td colSpan={4} className="py-4 text-center text-foreground-muted text-xs">{tc('no_teacher_data')}</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {profile.at_risk_classrooms.length > 0 && (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
              <h3 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                At-Risk Classrooms
              </h3>
              <div className="space-y-2">
                {profile.at_risk_classrooms.map(cr => (
                  <div key={cr.class_id} className="flex items-center justify-between text-sm">
                    <span className="text-foreground">{cr.name}</span>
                    <span className="text-red-400 font-medium">{cr.health.toFixed(0)} health - {cr.risk_student_count} at risk</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {!loadingProfile && !error && !profile && selectedId && (
        <div className="text-center py-12">
          <School className="w-10 h-10 text-border mx-auto mb-2" />
          <p className="text-foreground-muted text-sm">{ts('no_school_data')}</p>
        </div>
      )}
    </div>
  )
}
