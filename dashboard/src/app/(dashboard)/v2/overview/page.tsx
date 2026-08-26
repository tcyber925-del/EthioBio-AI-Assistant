'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { initAuth, isAuthenticated, getUserRole } from '@/lib/auth'
import { DashboardLayout, DashboardSkeleton } from '@/components/dashboard-v2'
import { StudentDashboard, TeacherDashboard, ParentDashboard, SchoolDashboard, AdminDashboard } from '@/components/dashboard-v2/dashboards'

const KNOWN_ROLES = ['student', 'parent', 'admin', 'teacher', 'school']

export default function V2OverviewPage() {
  const t = useTranslations('v2.nav')
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [role, setRole] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // Rebuild the in-memory role from /auth/me — the user_role cookie is a
    // 1-day cache and may be expired while the session token is still valid.
    initAuth().then(() => {
      if (cancelled) return
      if (!isAuthenticated()) { router.push('/login'); return }
      const r = getUserRole()
      if (!r || !KNOWN_ROLES.includes(r)) { router.push('/login'); return }
      setRole(r)
      setReady(true)
    })
    return () => { cancelled = true }
  }, [router])

  if (!ready) return <DashboardSkeleton />

  const renderDashboard = () => {
    switch (role) {
      case 'student': return <StudentDashboard />
      case 'parent': return <ParentDashboard />
      case 'admin': return <AdminDashboard />
      case 'teacher': return <TeacherDashboard />
      case 'school': return <SchoolDashboard />
      default: return null
    }
  }

  return (
    <DashboardLayout breadcrumbs={[{ label: t('overview') }]}>
      {renderDashboard()}
    </DashboardLayout>
  )
}
