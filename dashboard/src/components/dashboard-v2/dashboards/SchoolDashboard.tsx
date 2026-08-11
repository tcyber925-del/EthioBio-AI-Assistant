'use client'

import { useEffect, useState } from 'react'
import { ChevronDown, Shield } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { HeroSection, InsightCard, MetricStrip, AIInsightPanel } from '@/components/dashboard-v2'
import { ErrorState, ErrorBanner } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

interface SchoolItem { id: string; name: string }
interface TeacherMetric {
  teacher_id: string; classroom_count: number
  avg_student_readiness: number; intervention_rate: number; active_plan_count: number
}
interface SchoolProfile {
  school_id: string; total_teachers: number; total_classrooms: number; total_students: number
  avg_health: number; health_distribution: Record<string, number>
  teacher_metrics: TeacherMetric[]
  at_risk_classrooms: { class_id: string; name: string; health: number; risk_student_count: number }[]
}
interface TrendPoint {
  snapshot_date: string; avg_health: number; total_students: number; at_risk_count: number
}

type TFn = (key: string, values?: Record<string, string | number>) => string

function deriveSchoolInsights(profile: SchoolProfile, trends: TrendPoint[], t: TFn): string[] {
  const insights: string[] = []
  const riskTotal = profile.at_risk_classrooms.reduce((s, c) => s + c.risk_student_count, 0)
  if (riskTotal > 0) insights.push(t('insight_intervention', { students: riskTotal, classrooms: profile.at_risk_classrooms.length }))
  if (trends.length >= 2) {
    const latest = trends[trends.length - 1]
    const prev = trends[trends.length - 2]
    const diff = latest.avg_health - prev.avg_health
    if (diff > 0) insights.push(t('insight_health_up', { points: diff.toFixed(1) }))
    else if (diff < 0) insights.push(t('insight_health_down', { points: Math.abs(diff).toFixed(1) }))
  }
  const critical = profile.health_distribution['Critical'] || 0
  if (critical > 0) insights.push(t('insight_critical', { count: critical }))
  return insights
}

const BAND_LABEL_KEYS: Record<string, string> = {
  Strong: 'band_strong',
  Ready: 'band_ready',
  Developing: 'band_developing',
  Critical: 'band_critical',
}

export function SchoolDashboard() {
  const t = useTranslations('v2.school')
  const tcr = useTranslations('classroom')
  const tc = useTranslations('common')
  const [schools, setSchools] = useState<SchoolItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [profile, setProfile] = useState<SchoolProfile | null>(null)
  const [trends, setTrends] = useState<TrendPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)
  const [schoolError, setSchoolError] = useState<AppError | null>(null)

  const fetchSchools = async () => {
    setLoading(true); setError(null)
    try {
      const response = await fetchWithAuth('/teacher/schools')
      const d = await response.json()
      const schoolsList = d.schools || d || []
      setSchools(schoolsList)
      if (schoolsList[0]?.id) setSelectedId(schoolsList[0].id)
    } catch (err) {
      setError(normalizeException(err))
    } finally { setLoading(false) }
  }

  const fetchSchoolData = async (schoolId: string) => {
    setProfile(null)
    setTrends([])
    setSchoolError(null)
    try {
      const [p, t] = await Promise.allSettled([
        fetchWithAuth(`/teacher/schools/${schoolId}/overview`).then(r => r.json()),
        fetchWithAuth(`/teacher/schools/${schoolId}/trends?days=30`).then(r => r.json()),
      ])
      if (p.status === 'fulfilled') setProfile(p.value)
      else setSchoolError(normalizeException(p.reason))
      if (t.status === 'fulfilled') setTrends(t.value.trends || t.value || [])
    } catch {
      // partial data ok
    }
  }

  useEffect(() => { fetchSchools() }, [])
  useEffect(() => { if (selectedId) fetchSchoolData(selectedId) }, [selectedId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 rounded-full border-2 border-v2-accent border-t-transparent animate-spin mx-auto" />
      </div>
    )
  }

  if (error) {
    return <ErrorState error={error} title={t('load_error')} onRetry={() => void fetchSchools()} />
  }

  return (
    <>
      <HeroSection
        title={t('title')}
        subtitle={schools.length > 0 ? t('subtitle_schools', { count: schools.length }) : t('subtitle_none')}
        secondary={profile ? t('secondary_stats', { students: profile.total_students, teachers: profile.total_teachers, classrooms: profile.total_classrooms }) : undefined}
      />

      {schools.length > 1 && (
        <div className="mb-6 relative">
          <select
            value={selectedId || ''}
            onChange={e => setSelectedId(e.target.value)}
            className="appearance-none bg-v2-surface border border-v2-border rounded-xl px-4 pr-10 h-10 text-sm text-v2-text-primary outline-none focus:border-v2-accent transition-colors"
          >
            {schools.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-v2-text-secondary pointer-events-none" />
        </div>
      )}

      {profile ? (
        <>
          <div className="mb-6">
            <MetricStrip metrics={[
              { label: t('metric_avg_health'), value: `${profile.avg_health.toFixed(0)}%`, accent: true },
              { label: t('metric_teachers'), value: profile.total_teachers.toString() },
              { label: t('metric_classrooms'), value: profile.total_classrooms.toString() },
              { label: t('metric_at_risk'), value: profile.at_risk_classrooms.length.toString() },
            ]} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Health Distribution */}
              <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
                <h2 className="text-lg font-semibold text-v2-text-primary mb-4">{t('health_distribution')}</h2>
                <div className="space-y-3">
                  {Object.entries({
                    Strong: profile.health_distribution['Strong'] || 0,
                    Ready: profile.health_distribution['Ready'] || 0,
                    Developing: profile.health_distribution['Developing'] || 0,
                    Critical: profile.health_distribution['Critical'] || 0,
                  }).map(([band, count]) => {
                    const total = Object.values(profile.health_distribution).reduce((s, v) => s + v, 0)
                    const pct = total > 0 ? (count / total) * 100 : 0
                    return (
                      <div key={band} className="flex items-center gap-3">
                        <span className="text-sm text-v2-text-secondary w-24 shrink-0">{BAND_LABEL_KEYS[band] ? tcr(BAND_LABEL_KEYS[band]) : band}</span>
                        <div className="flex-1 h-2 bg-v2-border rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: band === 'Strong' ? 'var(--band-strong)' : band === 'Ready' ? 'var(--band-ready)' : band === 'Developing' ? 'var(--band-developing)' : 'var(--band-critical)',
                            }}
                          />
                        </div>
                        <span className="text-xs font-mono text-v2-text-secondary w-8 text-right">{count}</span>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Health Trend */}
              {trends.length > 0 && (
                <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
                  <h2 className="text-lg font-semibold text-v2-text-primary mb-4">{t('health_trend')}</h2>
                  <div className="space-y-1.5">
                    {trends.slice(-14).map((tp, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <span className="text-xs text-v2-text-secondary w-24 shrink-0">{tp.snapshot_date}</span>
                        <div className="flex-1 h-1.5 bg-v2-border rounded-full overflow-hidden">
                          <div className="h-full rounded-full bg-v2-accent transition-all duration-500" style={{ width: `${tp.avg_health}%` }} />
                        </div>
                        <span className="text-xs font-mono text-v2-text-secondary w-8 text-right">{tp.avg_health.toFixed(0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* At-Risk Classrooms */}
              {profile.at_risk_classrooms.length > 0 && (
                <div className="bg-v2-surface rounded-[20px] border border-v2-error/20 p-6">
                  <h2 className="text-lg font-semibold text-v2-text-primary mb-4">{t('at_risk_classrooms')}</h2>
                  <div className="space-y-2">
                    {profile.at_risk_classrooms.map(c => (
                      <div key={c.class_id} className="flex items-center justify-between p-3 rounded-xl bg-v2-bg">
                        <div>
                          <p className="text-sm font-medium text-v2-text-primary">{c.name}</p>
                          <p className="text-xs text-v2-text-secondary">{t('students_at_risk', { count: c.risk_student_count })}</p>
                        </div>
                        <span className={`text-sm font-mono ${c.health < 40 ? 'text-v2-error' : 'text-v2-warning'}`}>{c.health.toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-6">
              {/* Teacher Activity Summary */}
              <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
                <h2 className="text-lg font-semibold text-v2-text-primary mb-4">{t('teacher_activity')}</h2>
                {profile.teacher_metrics.length > 0 ? (
                  <div className="space-y-2">
                    {profile.teacher_metrics.slice(0, 10).map(tm => (
                      <div key={tm.teacher_id} className="flex items-center justify-between py-1.5 border-b border-v2-border/50 last:border-0">
                        <div className="flex items-center gap-2">
                          <Shield className="w-3.5 h-3.5 text-v2-text-secondary" />
                          <span className="text-sm text-v2-text-primary truncate max-w-[120px]">{tm.teacher_id.slice(0, 8)}</span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-v2-text-secondary">
                          <span>{t('classes_label', { count: tm.classroom_count })}</span>
                          <span>{t('avg_label', { pct: tm.avg_student_readiness.toFixed(0) })}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-v2-text-secondary">{t('no_teacher_data')}</p>
                )}
              </div>
              <AIInsightPanel insights={deriveSchoolInsights(profile, trends, t)} />
            </div>
          </div>
        </>
      ) : schoolError ? (
        <div className="mb-6">
          <ErrorBanner error={schoolError} actionLabel={tc('retry')} onAction={() => void (selectedId && fetchSchoolData(selectedId))} />
        </div>
      ) : (
        <div className="bg-v2-surface rounded-[20px] border border-v2-border p-12 text-center">
          <p className="text-sm text-v2-text-secondary">{t('select_school')}</p>
        </div>
      )}
    </>
  )
}
