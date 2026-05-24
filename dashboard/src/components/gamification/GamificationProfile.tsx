'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { fetchWithTimeout } from '@/lib/fetch'
import { CardSkeleton } from '@/components/Skeleton'
import XpCard from './XpCard'
import StreakWidget from './StreakWidget'
import MasteryProgressBar from './MasteryProgressBar'
import AchievementPanel from './AchievementPanel'
import RecoveryProgressCard from './RecoveryProgressCard'

interface Achievement {
  id: string
  title: string
  description: string
  icon: string
  unlocked_at: string | null
}

interface RecoveryProgress {
  active_plans: number
  total_tasks: number
  completed_tasks: number
  overall_progress_pct: number
}

interface GamificationData {
  total_xp: number
  level: number
  current_streak: number
  longest_streak: number
  next_level_xp: number
  progress_pct: number
  achievements: Achievement[]
  recovery_progress?: RecoveryProgress | null
}

export default function GamificationProfile({ userId }: { userId: string }) {
  const [data, setData] = useState<GamificationData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchProfile = async () => {
    setLoading(true)
    try {
      const d = await fetchWithTimeout(`/gamification/profile/${userId}`)
      setData(d)
      setError(null)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      if (message.includes('404') || message.includes('Not Found')) {
        setData(null)
        setError(null)
      } else {
        setError(message)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchProfile() }, [userId])

  if (loading) {
    return (
      <div className="space-y-4">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-card rounded-xl border border-border p-5 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-sm text-red-400 mb-2">{error}</p>
        <button onClick={fetchProfile} className="text-xs text-primary hover:underline flex items-center gap-1 mx-auto">
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      </div>
    )
  }

  if (!data) {
    return null
  }

  const allAchievements = [
    ...data.achievements,
    ...getLockedAchievements(data.achievements),
  ]

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
        Gamification
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MasteryProgressBar
          level={data.level}
          totalXp={data.total_xp}
          nextLevelXp={data.next_level_xp}
          progressPct={data.progress_pct}
        />
        <StreakWidget
          currentStreak={data.current_streak}
          longestStreak={data.longest_streak}
        />
      </div>

      <XpCard
        totalXp={data.total_xp}
        level={data.level}
        nextLevelXp={data.next_level_xp}
        progressPct={data.progress_pct}
      />

      {data.recovery_progress && (
        <RecoveryProgressCard
          activePlans={data.recovery_progress.active_plans}
          totalTasks={data.recovery_progress.total_tasks}
          completedTasks={data.recovery_progress.completed_tasks}
          overallProgressPct={data.recovery_progress.overall_progress_pct}
        />
      )}

      <AchievementPanel achievements={allAchievements} />
    </div>
  )
}

const ACHIEVEMENT_DEFINITIONS: Achievement[] = [
  { id: 'first_quiz', title: 'First Steps', description: 'Complete your first quiz', icon: 'medal', unlocked_at: null },
  { id: 'quiz_master', title: 'Quiz Master', description: 'Complete 10 quizzes', icon: 'medal', unlocked_at: null },
  { id: 'perfect_score', title: 'Perfect Score', description: 'Get 100% on any quiz', icon: 'medal', unlocked_at: null },
  { id: 'streak_3', title: 'Streak Starter', description: '3-day study streak', icon: 'medal', unlocked_at: null },
  { id: 'streak_7', title: 'Dedicated', description: '7-day study streak', icon: 'medal', unlocked_at: null },
  { id: 'streak_30', title: 'Scholar', description: '30-day study streak', icon: 'medal', unlocked_at: null },
  { id: 'xp_1000', title: 'XP Hunter', description: 'Earn 1000 total XP', icon: 'medal', unlocked_at: null },
  { id: 'level_5', title: 'Biology Expert', description: 'Reach Level 5', icon: 'medal', unlocked_at: null },
  { id: 'level_10', title: 'Master Biologist', description: 'Reach Level 10', icon: 'medal', unlocked_at: null },
]

function getLockedAchievements(unlocked: Achievement[]): Achievement[] {
  const unlockedIds = new Set(unlocked.map(a => a.id))
  return ACHIEVEMENT_DEFINITIONS.filter(a => !unlockedIds.has(a.id))
}
