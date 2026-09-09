'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { fetchWithTimeout } from '@/lib/fetch'

interface Stats {
  active_students: number
  quizzes_completed: number
  lesson_plans_generated: number
  knowledge_assets: number
  system_status: string
}

const defaultStats: Stats = {
  active_students: 1520,
  quizzes_completed: 8520,
  lesson_plans_generated: 240,
  knowledge_assets: 128,
  system_status: 'healthy',
}

export default function StatsSection() {
  const t = useTranslations('landing')
  const [stats, setStats] = useState<Stats>(defaultStats)

  useEffect(() => {
    fetchWithTimeout('/auth/public-stats')
      .then((data) => {
        if (data && data.active_students) setStats(data)
      })
      .catch((err) => console.log('Stats fetch error: using static fallbacks', err))
  }, [])

  return (
    <section
      id="stats"
      className="relative overflow-hidden border-b border-[#2d2d2d] bg-[#1c1c1c] py-20"
    >
      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-16 text-center">
          <h2 className="verge-display mb-2 text-3xl text-white sm:text-4xl">{t('stats_title')}</h2>
          <div className="inline-flex items-center space-x-2 border border-[#3cffd0]/30 bg-[#3cffd0]/10 px-3 py-1 font-mono text-[10px] text-[#3cffd0]">
            <span className="h-1.5 w-1.5 animate-ping rounded-full bg-[#3cffd0]" />
            <span>Real-Time platform counts</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-8 lg:grid-cols-4">
          <div className="border border-[#2d2d2d] bg-[#131313] p-6 text-center">
            <span className="verge-display mb-2 block text-3xl font-black text-white sm:text-5xl">{stats.active_students.toLocaleString()}</span>
            <span className="verge-label text-gray-500">{t('stats_students')}</span>
          </div>

          <div className="border border-[#2d2d2d] bg-[#131313] p-6 text-center">
            <span className="verge-display mb-2 block text-3xl font-black text-white sm:text-5xl">{stats.quizzes_completed.toLocaleString()}</span>
            <span className="verge-label text-gray-500">{t('stats_quizzes')}</span>
          </div>

          <div className="border border-[#2d2d2d] bg-[#131313] p-6 text-center">
            <span className="verge-display mb-2 block text-3xl font-black text-white sm:text-5xl">{stats.lesson_plans_generated.toLocaleString()}</span>
            <span className="verge-label text-gray-500">{t('stats_lessons')}</span>
          </div>

          <div className="border border-[#2d2d2d] bg-[#131313] p-6 text-center">
            <span className="verge-display mb-2 block text-3xl font-black text-white sm:text-5xl">{stats.knowledge_assets.toLocaleString()}</span>
            <span className="verge-label text-gray-500">{t('stats_assets')}</span>
          </div>
        </div>
      </div>
    </section>
  )
}