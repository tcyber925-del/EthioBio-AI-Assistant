'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { ArrowLeft, AlertTriangle, RefreshCw, Clock, Calendar, BookOpen, Target, ChevronDown, ChevronRight } from 'lucide-react'
import { CardSkeleton } from '@/components/Skeleton'
import MarkdownRenderer from '@/components/MarkdownRenderer'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { isAuthenticated } from '@/lib/auth'

export const dynamic = 'force-dynamic'

interface Period {
  name: string; duration_minutes: number
  objective?: string; description: string; activity_type: string
  teacher_activity?: string; student_activity?: string
  materials_needed?: string[]
}

interface LessonPlanDetail {
  objective: string; prior_knowledge: string | null
  explanation: string; activities: any[]
  assessment: string; homework: string | null; teacher_notes: string | null
  model_used: string; periods?: Period[]
}

interface DayLesson {
  day_index: number; subtopic: string; objective: string
  lesson: LessonPlanDetail
}

interface UnitPlanDetail {
  id: string; unit_title: string; grade_level: number
  topic: string; days: number; language: string
  model_used: string | null; created_at: string | null
  lessons: DayLesson[]
}

export default function UnitPlanDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [plan, setPlan] = useState<UnitPlanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedDays, setExpandedDays] = useState<Set<number>>(new Set())
  const t = useTranslations('unit_plans')

  const fetchPlan = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchWithAuth(`/api/lesson-plan/unit/${params.id}`)
      setPlan(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    fetchPlan()
  }, [params.id, router])

  const toggleDay = (idx: number) => {
    setExpandedDays(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx); else next.add(idx)
      return next
    })
  }

  if (loading) return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}</div>
  if (error) return (
    <div className="text-center py-16">
      <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
      <p className="text-red-400">{error}</p>
      <div className="mt-4 flex gap-3 justify-center">
        <button onClick={fetchPlan} className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors">
          <RefreshCw className="w-4 h-4 inline mr-1" /> Retry
        </button>
        <Link href="/unit-plans" className="px-4 py-2 bg-card border border-border text-foreground rounded-lg text-sm hover:bg-border transition-colors">
          {t('back')}
        </Link>
      </div>
    </div>
  )
  if (!plan) return null

  return (
    <div>
      <Link href="/unit-plans" className="flex items-center gap-2 text-sm text-foreground-muted hover:text-foreground mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" /> {t('back')}
      </Link>

      <div className="bg-gradient-to-br from-primary/5 to-transparent rounded-xl border border-border p-6 mb-6">
        <h1 className="text-2xl font-bold text-foreground mb-2">{plan.unit_title}</h1>
        <div className="flex flex-wrap gap-4 text-sm text-foreground-muted">
          <span className="flex items-center gap-1"><BookOpen className="w-4 h-4" /> {t('col_topic')}: {plan.topic}</span>
          <span className="flex items-center gap-1"><Target className="w-4 h-4" /> {t('col_grade')} {plan.grade_level}</span>
          <span className="flex items-center gap-1"><Calendar className="w-4 h-4" /> {t('details_days')}: {plan.days}</span>
          <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> {t('details_duration')}: {plan.model_used}</span>
        </div>
        <p className="text-xs text-foreground-muted mt-3">{t('details_created')} {plan.created_at?.slice(0, 10)}</p>
      </div>

      <div className="space-y-4">
        {plan.lessons
          .sort((a, b) => a.day_index - b.day_index)
          .map((day) => (
            <div key={day.day_index} className="bg-card rounded-xl border border-border overflow-hidden">
              <button
                onClick={() => toggleDay(day.day_index)}
                className="w-full flex items-center justify-between p-4 hover:bg-background-secondary/50 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm shrink-0">
                    {day.day_index}
                  </div>
                  <div>
                    <p className="font-medium text-foreground">
                      {t('day_lesson', { day: day.day_index, subtopic: day.subtopic })}
                    </p>
                    <p className="text-xs text-foreground-muted mt-0.5 line-clamp-1">{day.objective}</p>
                  </div>
                </div>
                {expandedDays.has(day.day_index) ? <ChevronDown className="w-5 h-5 text-foreground-muted" /> : <ChevronRight className="w-5 h-5 text-foreground-muted" />}
              </button>

              {expandedDays.has(day.day_index) && (
                <div className="px-4 pb-4 space-y-4 border-t border-border">
                  <div className="pt-4">
                    <h4 className="text-sm font-medium text-foreground-muted mb-1">{t('day_objective')}</h4>
                    <MarkdownRenderer content={day.lesson.objective} className="text-foreground text-sm" />
                  </div>

                  {day.lesson.prior_knowledge && (
                    <div>
                      <h4 className="text-sm font-medium text-foreground-muted mb-1">Prior Knowledge</h4>
                      <MarkdownRenderer content={day.lesson.prior_knowledge} className="text-foreground text-sm" />
                    </div>
                  )}

                  {day.lesson.explanation && (
                    <div>
                      <h4 className="text-sm font-medium text-foreground-muted mb-1">Explanation</h4>
                      <MarkdownRenderer content={day.lesson.explanation} className="text-foreground text-sm" />
                    </div>
                  )}

                  {day.lesson.periods && day.lesson.periods.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-foreground-muted mb-2">{t('day_periods')} ({day.lesson.periods.length})</h4>
                      <div className="space-y-2">
                        {day.lesson.periods.map((p, i) => (
                          <div key={i} className="p-3 bg-background-secondary rounded-lg text-sm border-l-4 border-primary">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-foreground">{p.name}</span>
                              <span className="text-foreground-muted text-xs">({p.duration_minutes}min · {p.activity_type})</span>
                            </div>
                            {p.objective && <p className="text-xs text-foreground-muted mb-1"><span className="font-medium">Objective:</span> {p.objective}</p>}
                            <p className="text-foreground-muted">{p.description}</p>
                            <div className="mt-1 grid grid-cols-2 gap-1 text-xs text-foreground-muted">
                              {p.teacher_activity && <p><span className="font-medium">Teacher:</span> {p.teacher_activity}</p>}
                              {p.student_activity && <p><span className="font-medium">Students:</span> {p.student_activity}</p>}
                            </div>
                            {p.materials_needed && p.materials_needed.length > 0 && (
                              <p className="text-xs text-foreground-muted mt-1">
                                <span className="font-medium">Materials:</span> {p.materials_needed.join(', ')}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {day.lesson.activities && day.lesson.activities.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-foreground-muted mb-2">{t('day_activities')} ({day.lesson.activities.length})</h4>
                      <div className="space-y-2">
                        {day.lesson.activities.map((a: any, i: number) => (
                          <div key={i} className="p-3 bg-background-secondary rounded-lg text-sm">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-foreground">{a.name}</span>
                              <span className="text-foreground-muted text-xs">({a.duration_minutes}min · {a.type})</span>
                            </div>
                            <p className="text-foreground-muted mt-1">{a.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {day.lesson.assessment && (
                    <div>
                      <h4 className="text-sm font-medium text-foreground-muted mb-1">{t('day_assessment')}</h4>
                      <MarkdownRenderer content={day.lesson.assessment} className="text-foreground text-sm" />
                    </div>
                  )}

                  {day.lesson.homework && (
                    <div>
                      <h4 className="text-sm font-medium text-foreground-muted mb-1">{t('day_homework')}</h4>
                      <MarkdownRenderer content={day.lesson.homework} className="text-foreground text-sm" />
                    </div>
                  )}

                  {day.lesson.teacher_notes && (
                    <div>
                      <h4 className="text-sm font-medium text-foreground-muted mb-1">{t('day_teacher_notes')}</h4>
                      <MarkdownRenderer content={day.lesson.teacher_notes} className="text-foreground text-sm italic" />
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
      </div>
    </div>
  )
}
