'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated, getUserRole } from '@/lib/auth'
import { DashboardLayout, DashboardSkeleton } from '@/components/dashboard-v2'
import { StudentDashboard, TeacherDashboard, ParentDashboard, SchoolDashboard, AdminDashboard } from '@/components/dashboard-v2/dashboards'

export default function V2OverviewPage() {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [role, setRole] = useState<string | null>(null)

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    setRole(getUserRole())
    setReady(true)
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
    <DashboardLayout breadcrumbs={[{ label: 'Overview' }]}>
      {renderDashboard()}
    </DashboardLayout>
  )
}
