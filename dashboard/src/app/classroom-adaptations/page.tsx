'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  GraduationCap, Users, Activity, Brain,
  CheckCircle, Clock, AlertTriangle, Target,
  Loader2, BookOpen, ChevronRight,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-v2'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface LessonPlanSummary {
  id: string
  objective: string
  topic: string
  grade_level: number
  classroom_id: string | null
  rating: number | null
  used_in_class: boolean
  created_at: string | null
  classroom_context: {
    classroom_health: string
    readiness_distribution: Record<string, number>
    at_risk_count: number
    health_heatmap: Record<string, Record<string, number>>
    misconceptions: { by_topic: { topic: string; top_pattern: string; affected_students: number }[] }
    prerequisite_gaps: { topic: string; affected_count: number; total_checked: number }[]
    recommended_strategies: { intervention_type: string; avg_effectiveness: number }[]
  } | null
}

export default function ClassroomAdaptationsPage() {
  const router = useRouter()
  const [plans, setPlans] = useState<LessonPlanSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchPlans()
  }, [router])

  const fetchPlans = async () => {
    setLoading(true)
    try {
      const data = await fetchWithAuth('/lesson-plan/?limit=50')
      setPlans(Array.isArray(data) ? data : [])
    } catch {
      setPlans([])
    } finally {
      setLoading(false)
    }
  }

  const adaptedPlans = plans.filter(p => p.classroom_id)
  const standardPlans = plans.filter(p => !p.classroom_id)
  const avgRating = adaptedPlans.length
    ? Math.round(adaptedPlans.reduce((s, p) => s + (p.rating || 0), 0) / adaptedPlans.length * 10) / 10
    : 0

  return (
    <DashboardLayout breadcrumbs={[{ label: 'Classroom Adaptations' }]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Classroom Adaptation Viewer</h1>
          <p className="text-sm text-foreground-muted mt-1">
            Lesson plans generated with classroom intelligence — showing how AI adapts content to each classroom
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-foreground-muted text-xs mb-1">
              <GraduationCap className="w-4 h-4" /> Adapted Lessons
            </div>
            <p className="text-2xl font-bold text-foreground">{adaptedPlans.length}</p>
          </div>
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-foreground-muted text-xs mb-1">
              <BookOpen className="w-4 h-4" /> Standard Lessons
            </div>
            <p className="text-2xl font-bold text-foreground">{standardPlans.length}</p>
          </div>
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-foreground-muted text-xs mb-1">
              <CheckCircle className="w-4 h-4" /> Used in Class
            </div>
            <p className="text-2xl font-bold text-foreground">{plans.filter(p => p.used_in_class).length}</p>
          </div>
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 text-foreground-muted text-xs mb-1">
              <Target className="w-4 h-4" /> Avg Rating
            </div>
            <p className="text-2xl font-bold text-foreground">{avgRating || '—'}</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-foreground-muted" />
          </div>
        ) : plans.length === 0 ? (
          <div className="text-center py-16 bg-card rounded-xl border border-border">
            <GraduationCap className="w-12 h-12 text-border mx-auto mb-3" />
            <p className="text-foreground-muted font-medium">No lesson plans found</p>
            <p className="text-sm text-foreground-muted/60 mt-1">Generate lesson plans with a classroom_id to see adaptations</p>
          </div>
        ) : (
          <div className="space-y-4">
            {adaptedPlans.map(plan => (
              <div key={plan.id} className="bg-card border border-border rounded-xl overflow-hidden">
                <button
                  onClick={() => setSelectedPlan(selectedPlan === plan.id ? null : plan.id)}
                  className="w-full flex items-center justify-between p-4 hover:bg-background-secondary/50 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <GraduationCap className="w-5 h-5 text-primary" />
                    <div>
                      <p className="font-medium text-foreground">{plan.topic}</p>
                      <p className="text-xs text-foreground-muted">
                        Grade {plan.grade_level} &middot; {plan.objective.slice(0, 80)}...
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {plan.rating && (
                      <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                        plan.rating >= 4 ? 'bg-green-500/10 text-green-400' :
                        plan.rating >= 3 ? 'bg-yellow-500/10 text-yellow-400' :
                        'bg-red-500/10 text-red-400'
                      }`}>{plan.rating}/5</span>
                    )}
                    {plan.used_in_class && (
                      <span className="text-xs bg-blue-500/10 text-blue-400 px-2 py-1 rounded-full">Used</span>
                    )}
                    <ChevronRight className={`w-4 h-4 text-foreground-muted transition-transform ${selectedPlan === plan.id ? 'rotate-90' : ''}`} />
                  </div>
                </button>

                {selectedPlan === plan.id && plan.classroom_context && (
                  <div className="border-t border-border px-4 py-4 space-y-4 bg-background-secondary/30">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="bg-card rounded-lg border border-border p-3">
                        <div className="flex items-center gap-2 text-foreground-muted text-xs mb-2">
                          <Activity className="w-3 h-3" /> Classroom Health
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${
                            plan.classroom_context.classroom_health === 'healthy' ? 'bg-green-400' :
                            plan.classroom_context.classroom_health === 'needs_attention' ? 'bg-yellow-400' : 'bg-red-400'
                          }`} />
                          <span className="text-sm font-medium text-foreground capitalize">
                            {plan.classroom_context.classroom_health.replace('_', ' ')}
                          </span>
                        </div>
                        {plan.classroom_context.at_risk_count > 0 && (
                          <p className="text-xs text-red-400 mt-1">
                            <AlertTriangle className="w-3 h-3 inline mr-1" />
                            {plan.classroom_context.at_risk_count} at-risk student{plan.classroom_context.at_risk_count > 1 ? 's' : ''}
                          </p>
                        )}
                      </div>

                      <div className="bg-card rounded-lg border border-border p-3">
                        <div className="flex items-center gap-2 text-foreground-muted text-xs mb-2">
                          <Brain className="w-3 h-3" /> Misconceptions
                        </div>
                        {(plan.classroom_context.misconceptions?.by_topic || []).length > 0 ? (
                          <div className="space-y-1">
                            {plan.classroom_context.misconceptions.by_topic.slice(0, 3).map((mc, i) => (
                              <p key={i} className="text-xs text-foreground">
                                <span className="font-medium">{mc.topic}:</span>{' '}
                                {mc.top_pattern.slice(0, 60)}
                                <span className="text-foreground-muted"> ({mc.affected_students})</span>
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-foreground-muted">No misconceptions detected</p>
                        )}
                      </div>

                      <div className="bg-card rounded-lg border border-border p-3">
                        <div className="flex items-center gap-2 text-foreground-muted text-xs mb-2">
                          <Clock className="w-3 h-3" /> Prerequisite Gaps
                        </div>
                        {(plan.classroom_context.prerequisite_gaps || []).length > 0 ? (
                          <div className="space-y-1">
                            {plan.classroom_context.prerequisite_gaps.map((g, i) => (
                              <p key={i} className="text-xs text-foreground">
                                {g.topic}: <span className="text-yellow-400">{g.affected_count}/{g.total_checked}</span> affected
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-foreground-muted">No gaps found</p>
                        )}
                      </div>
                    </div>

                    {(plan.classroom_context.recommended_strategies || []).length > 0 && (
                      <div className="bg-card rounded-lg border border-border p-3">
                        <div className="flex items-center gap-2 text-foreground-muted text-xs mb-2">
                          <Target className="w-3 h-3" /> Recommended Strategies
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {plan.classroom_context.recommended_strategies.map((s, i) => (
                            <span key={i} className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary text-xs rounded-full">
                              {s.intervention_type.replace(/_/g, ' ')}
                              <span className="text-foreground-muted">({Math.round(s.avg_effectiveness)}%)</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex justify-end">
                      <Link
                        href={`/lessons/${plan.id}`}
                        className="text-xs text-primary hover:underline flex items-center gap-1"
                      >
                        View full lesson <ChevronRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {standardPlans.length > 0 && (
              <details className="bg-card border border-border rounded-xl">
                <summary className="p-4 text-sm font-medium text-foreground-muted cursor-pointer hover:text-foreground transition-colors">
                  Standard Lessons (no classroom adaptation) &middot; {standardPlans.length}
                </summary>
                <div className="border-t border-border divide-y divide-border">
                  {standardPlans.map(plan => (
                    <Link key={plan.id} href={`/lessons/${plan.id}`} className="flex items-center justify-between p-3 hover:bg-background-secondary/50 transition-colors">
                      <div>
                        <p className="text-sm text-foreground">{plan.topic}</p>
                        <p className="text-xs text-foreground-muted">Grade {plan.grade_level}</p>
                      </div>
                      <ChevronRight className="w-4 h-4 text-foreground-muted" />
                    </Link>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
