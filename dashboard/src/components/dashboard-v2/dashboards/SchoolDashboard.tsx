'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw, ChevronDown, Shield } from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { HeroSection, InsightCard, MetricStrip, AIInsightPanel } from '@/components/dashboard-v2'

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

function deriveSchoolInsights(profile: SchoolProfile, trends: TrendPoint[]): string[] {
  const insights: string[] = []
  const riskTotal = profile.at_risk_classrooms.reduce((s, c) => s + c.risk_student_count, 0)
  if (riskTotal > 0) insights.push(`${riskTotal} student${riskTotal > 1 ? 's' : ''} across ${profile.at_risk_classrooms.length} classroom${profile.at_risk_classrooms.length > 1 ? 's' : ''} need intervention.`)
  if (trends.length >= 2) {
    const latest = trends[trends.length - 1]
    const prev = trends[trends.length - 2]
    const diff = latest.avg_health - prev.avg_health
    if (diff > 0) insights.push(`School health increased by ${diff.toFixed(1)} points since last snapshot.`)
    else if (diff < 0) insights.push(`School health decreased by ${Math.abs(diff).toFixed(1)} points. Review at-risk classrooms.`)
  }
  const critical = profile.health_distribution['Critical'] || 0
  if (critical > 0) insights.push(`${critical} student${critical > 1 ? 's' : ''} in critical readiness band. Immediate intervention recommended.`)
  return insights
}

export function SchoolDashboard() {
  const [schools, setSchools] = useState<SchoolItem[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [profile, setProfile] = useState<SchoolProfile | null>(null)
  const [trends, setTrends] = useState<TrendPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchSchools = async () => {
    setLoading(true); setError(null)
    try {
      const d = await fetchWithAuth('/teacher/schools')
      const schoolsList = d.schools || d || []
      setSchools(schoolsList)
      if (schoolsList[0]?.id) setSelectedId(schoolsList[0].id)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally { setLoading(false) }
  }

  const fetchSchoolData = async (schoolId: string) => {
    setProfile(null)
    setTrends([])
    try {
      const [p, t] = await Promise.allSettled([
        fetchWithAuth(`/teacher/schools/${schoolId}/overview`),
        fetchWithAuth(`/teacher/schools/${schoolId}/trends?days=30`),
      ])
      if (p.status === 'fulfilled') setProfile(p.value)
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
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-10 h-10 text-v2-error mx-auto mb-3" />
          <p className="text-sm font-medium text-v2-text-secondary mb-4">{error}</p>
          <button onClick={fetchSchools} className="inline-flex items-center gap-2 px-4 h-9 rounded-xl bg-v2-accent text-v2-inverted text-sm font-medium hover:bg-white transition-colors">
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <>
      <HeroSection
        title="School Health Overview"
        subtitle={schools.length > 0 ? `${schools.length} school${schools.length > 1 ? 's' : ''} managed` : 'No schools found'}
        secondary={profile ? `${profile.total_students} students · ${profile.total_teachers} teachers · ${profile.total_classrooms} classrooms` : undefined}
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
              { label: 'Avg Health', value: `${profile.avg_health.toFixed(0)}%`, accent: true },
              { label: 'Teachers', value: profile.total_teachers.toString() },
              { label: 'Classrooms', value: profile.total_classrooms.toString() },
              { label: 'At-Risk Classes', value: profile.at_risk_classrooms.length.toString() },
            ]} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="lg:col-span-2 space-y-6">
              {/* Health Distribution */}
              <div className="bg-v2-surface rounded-[20px] border border-v2-border p-6">
                <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Health Distribution</h2>
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
                        <span className="text-sm text-v2-text-secondary w-24 shrink-0">{band}</span>
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
                  <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Health Trend (30 days)</h2>
                  <div className="space-y-1.5">
                    {trends.slice(-14).map((t, i) => (
                      <div key={i} className="flex items-center gap-3">
                        <span className="text-xs text-v2-text-secondary w-24 shrink-0">{t.snapshot_date}</span>
                        <div className="flex-1 h-1.5 bg-v2-border rounded-full overflow-hidden">
                          <div className="h-full rounded-full bg-v2-accent transition-all duration-500" style={{ width: `${t.avg_health}%` }} />
                        </div>
                        <span className="text-xs font-mono text-v2-text-secondary w-8 text-right">{t.avg_health.toFixed(0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* At-Risk Classrooms */}
              {profile.at_risk_classrooms.length > 0 && (
                <div className="bg-v2-surface rounded-[20px] border border-v2-error/20 p-6">
                  <h2 className="text-lg font-semibold text-v2-text-primary mb-4">At-Risk Classrooms</h2>
                  <div className="space-y-2">
                    {profile.at_risk_classrooms.map(c => (
                      <div key={c.class_id} className="flex items-center justify-between p-3 rounded-xl bg-v2-bg">
                        <div>
                          <p className="text-sm font-medium text-v2-text-primary">{c.name}</p>
                          <p className="text-xs text-v2-text-secondary">{c.risk_student_count} student{c.risk_student_count !== 1 ? 's' : ''} at risk</p>
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
                <h2 className="text-lg font-semibold text-v2-text-primary mb-4">Teacher Activity</h2>
                {profile.teacher_metrics.length > 0 ? (
                  <div className="space-y-2">
                    {profile.teacher_metrics.slice(0, 10).map(t => (
                      <div key={t.teacher_id} className="flex items-center justify-between py-1.5 border-b border-v2-border/50 last:border-0">
                        <div className="flex items-center gap-2">
                          <Shield className="w-3.5 h-3.5 text-v2-text-secondary" />
                          <span className="text-sm text-v2-text-primary truncate max-w-[120px]">{t.teacher_id.slice(0, 8)}</span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-v2-text-secondary">
                          <span>{t.classroom_count} classes</span>
                          <span>{t.avg_student_readiness.toFixed(0)}% avg</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-v2-text-secondary">No teacher data.</p>
                )}
              </div>
              <AIInsightPanel insights={deriveSchoolInsights(profile, trends)} />
            </div>
          </div>
        </>
      ) : (
        <div className="bg-v2-surface rounded-[20px] border border-v2-border p-12 text-center">
          <p className="text-sm text-v2-text-secondary">Select a school to view data.</p>
        </div>
      )}
    </>
  )
}
