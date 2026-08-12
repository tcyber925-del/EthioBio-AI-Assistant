'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { BookOpen, ClipboardCheck, FileText, Users, BarChart3, RefreshCw } from 'lucide-react'
import { getUserRole, isAuthenticated } from '@/lib/auth'
import { CardSkeleton, TableSkeleton } from '@/components/Skeleton'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import PageHeader from '@/components/ui/PageHeader'
import Card from '@/components/ui/Card'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/errors'
import { normalizeException, type AppError } from '@/lib/errors'

export const dynamic = 'force-dynamic'

interface DashboardData {
  users: number; teachers: number; students: number
  quizzes: number; lesson_plans: number; quiz_attempts: number
  recent_logs: Array<{
    id: string; request_type: string; model_used: string
    success: boolean; latency_ms: number; created_at: string
  }>
}

const statCards = [
  { key: 'users' as const, icon: Users, labelKey: 'total_users', subtitle: 'platform_users', color: 'blue' as const },
  { key: 'teachers' as const, icon: Users, labelKey: 'total_teachers', color: 'green' as const },
  { key: 'students' as const, icon: Users, labelKey: 'total_students', color: 'purple' as const },
  { key: 'quizzes' as const, icon: ClipboardCheck, labelKey: 'quizzes', color: 'orange' as const },
  { key: 'lesson_plans' as const, icon: FileText, labelKey: 'lesson_plans', color: 'indigo' as const },
  { key: 'quiz_attempts' as const, icon: BarChart3, labelKey: 'quiz_attempts', color: 'teal' as const },
]

const colorMap: Record<string, string> = {
  blue: 'bg-blue-500/10 text-blue-400',
  green: 'bg-green-500/10 text-green-400',
  purple: 'bg-purple-500/10 text-purple-400',
  orange: 'bg-orange-500/10 text-orange-400',
  indigo: 'bg-indigo-500/10 text-indigo-400',
  teal: 'bg-teal-500/10 text-teal-400',
}

export default function Dashboard() {
  const router = useRouter()
  const t = useTranslations('admin.dashboard')
  const tc = useTranslations('common')
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AppError | null>(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const endpoint = getUserRole() === 'admin' ? '/api/admin/dashboard' : '/api/teacher/dashboard'
      const response = await fetchWithAuth(endpoint)
      const d = await response.json()
      setData(d)
      setError(null)
    } catch (err) {
      setError(normalizeException(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
  }, [router])

  useEffect(() => {
    const role = getUserRole()
    if (role === 'student') { router.push('/student'); return }
    fetchData()
  }, [router])

  if (loading && !data) {
    return (
      <div>
        <div className="h-16 mb-8">
          <div className="animate-pulse bg-border/50 rounded-lg w-48 h-8" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
          {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
        <TableSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <ErrorState
        error={error}
        title={t('error_load')}
        onRetry={() => void fetchData()}
      />
    )
  }

  const logs = data?.recent_logs || []
  const successCount = logs.filter(l => l.success).length
  const failCount = logs.filter(l => !l.success).length

  const chartData = logs.slice().reverse().map((l, i) => ({
    name: `#${i + 1}`,
    latency: l.latency_ms,
    success: l.success ? 1 : 0,
  }))

  return (
    <div>
      <PageHeader
        icon={<BarChart3 className="w-6 h-6" />}
        title={t('dashboard')}
        description={t('subtitle')}
        actions={
          <Button variant="secondary" size="sm" onClick={fetchData}>
            <RefreshCw className="w-4 h-4" />
            {tc('refresh')}
          </Button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
        {statCards.map(({ key, icon: Icon, labelKey, subtitle, color }) => (
          <Card key={key}>
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg shrink-0 ${colorMap[color]}`}>
                <Icon className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <p className="text-small text-foreground-muted">{t(labelKey)}</p>
                <p className="text-display text-foreground">{data?.[key] ?? 0}</p>
                {subtitle && <p className="text-small text-foreground-muted/60 mt-0.5">{t(subtitle)}</p>}
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <Card className="lg:col-span-2" variant="elevated">
          <h2 className="text-heading text-foreground mb-5">{t('request_latency')}</h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a3454" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#8896b8' }} />
                <YAxis tick={{ fontSize: 11, fill: '#8896b8' }} unit="ms" />
                <Tooltip />
                <Line type="monotone" dataKey="latency" stroke="#34d399" strokeWidth={2} dot={{ r: 3, fill: '#34d399' }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-foreground-muted text-body py-8 text-center">{t('no_request_data')}</p>
          )}
        </Card>
        <Card>
          <h2 className="text-heading text-foreground mb-5">{t('request_status')}</h2>
          {logs.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-green-500/10">
                <span className="text-subhead text-green-400">{t('success')}</span>
                <span className="text-display text-green-400">{successCount}</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-red-500/10">
                <span className="text-subhead text-red-400">{t('failed')}</span>
                <span className="text-display text-red-400">{failCount}</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-border/50">
                <span className="text-subhead text-foreground-muted">{t('success_rate')}</span>
                <span className="text-heading text-foreground">
                  {logs.length > 0 ? Math.round(successCount / logs.length * 100) : 0}%
                </span>
              </div>
            </div>
          ) : (
            <p className="text-foreground-muted text-body py-8 text-center">{tc('no_data')}</p>
          )}
        </Card>
      </div>

      <Card className="p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h2 className="text-heading text-foreground">{t('recent_activity')}</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-background-secondary">
              <tr>
                <th className="px-6 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{tc('type')}</th>
                <th className="px-6 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{t('col_model')}</th>
                <th className="px-6 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{tc('status')}</th>
                <th className="px-6 py-3 text-left text-small font-medium text-foreground-muted uppercase tracking-wider">{t('col_latency')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {logs.slice(0, 10).map(log => (
                <tr key={log.id} className="hover:bg-background-secondary/30 transition-colors">
                  <td className="px-6 py-3.5 text-body text-foreground">{log.request_type}</td>
                  <td className="px-6 py-3.5 text-mono text-foreground-muted">{log.model_used}</td>
                  <td className="px-6 py-3.5">
                    <Badge variant={log.success ? 'green' : 'red'}>
                      {log.success ? t('success') : t('failed')}
                    </Badge>
                  </td>
                  <td className="px-6 py-3.5 text-mono text-foreground-muted">{log.latency_ms}ms</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr><td colSpan={4} className="px-6 py-12 text-center text-foreground-muted text-body">{t('no_activity')}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
