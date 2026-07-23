'use client'

import { useEffect, useState, useRef } from 'react'
import { useTranslations } from 'next-intl'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'
import { CardSkeleton } from '@/components/Skeleton'
import Card from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import XpCard from './XpCard'
import StreakWidget from './StreakWidget'
import MasteryProgressBar from './MasteryProgressBar'
import AchievementPanel from './AchievementPanel'
import RecoveryProgressCard from './RecoveryProgressCard'
import LevelUpModal from './LevelUpModal'

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
  level_up: boolean
  new_level: number
  achievements: Achievement[]
  recovery_progress?: RecoveryProgress | null
}

export default function GamificationProfile({ userId }: { userId: string }) {
  const tg = useTranslations('gamification')
  const tc = useTranslations('common')
  const [data, setData] = useState<GamificationData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showLevelUp, setShowLevelUp] = useState(false)
  const [levelUpLevel, setLevelUpLevel] = useState(0)
  const prevLevel = useRef<number | null>(null)

  const fetchProfile = async () => {
    setLoading(true)
    try {
      const response = await fetchWithAuth(`/gamification/profile/${userId}`)
      const d = await response.json()
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

  useEffect(() => {
    if (!data) return
    if (data.level_up && data.new_level > 0) {
      setLevelUpLevel(data.new_level)
      setShowLevelUp(true)
    } else if (prevLevel.current !== null && data.level > prevLevel.current) {
      setLevelUpLevel(data.level)
      setShowLevelUp(true)
    }
    prevLevel.current = data.level
  }, [data])

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
      <Card className="text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-small text-red-400 mb-2">{error}</p>
        <Button variant="ghost" size="sm" onClick={fetchProfile}>
          <RefreshCw className="w-3 h-3" />
          {tc('retry')}
        </Button>
      </Card>
    )
  }

  if (!data) {
    return null
  }

  const allAchievements = [
    ...data.achievements,
    ...getLockedAchievements(data.achievements, tg),
  ]

  return (
    <div className="space-y-4">
      <h2 className="text-heading text-foreground flex items-center gap-2">
        {tg('title')}
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

      {showLevelUp && (
        <LevelUpModal
          level={levelUpLevel}
          onClose={() => setShowLevelUp(false)}
        />
      )}
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

function getLockedAchievements(unlocked: Achievement[], t: (key: string) => string): Achievement[] {
  const unlockedIds = new Set(unlocked.map(a => a.id))
  return ACHIEVEMENT_DEFINITIONS.filter(a => !unlockedIds.has(a.id))
}
