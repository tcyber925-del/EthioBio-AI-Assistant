'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { isAuthenticated } from '@/lib/auth'
import { DashboardLayout, DashboardSkeleton } from '@/components/dashboard-v2'
import { SchoolDashboard } from '@/components/dashboard-v2/dashboards'

export default function SchoolPage() {
  const t = useTranslations('v2.nav')
  const router = useRouter()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/login'); return }
    setReady(true)
  }, [router])

  if (!ready) return <DashboardSkeleton />

  return (
    <DashboardLayout breadcrumbs={[{ label: t('school') }]}>
      <SchoolDashboard />
    </DashboardLayout>
  )
}
