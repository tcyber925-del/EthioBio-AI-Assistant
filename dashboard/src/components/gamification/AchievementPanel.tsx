'use client'

import { useTranslations } from 'next-intl'
import { Medal, Lock } from 'lucide-react'

interface Achievement {
  id: string
  title: string
  description: string
  icon: string
  unlocked_at: string | null
}

interface AchievementPanelProps {
  achievements: Achievement[]
}

const ACHIEVEMENT_KEY_MAP: Record<string, { title: string; desc: string }> = {
  first_quiz: { title: 'achievement_first_steps', desc: 'achievement_first_steps_desc' },
  quiz_master: { title: 'achievement_quiz_master', desc: 'achievement_quiz_master_desc' },
  perfect_score: { title: 'achievement_perfect_score', desc: 'achievement_perfect_score_desc' },
  streak_3: { title: 'achievement_streak_starter', desc: 'achievement_streak_starter_desc' },
  streak_7: { title: 'achievement_dedicated', desc: 'achievement_dedicated_desc' },
  streak_30: { title: 'achievement_scholar', desc: 'achievement_scholar_desc' },
  xp_1000: { title: 'achievement_xp_hunter', desc: 'achievement_xp_hunter_desc' },
  level_5: { title: 'achievement_biology_expert', desc: 'achievement_biology_expert_desc' },
  level_10: { title: 'achievement_master_biologist', desc: 'achievement_master_biologist_desc' },
}

export default function AchievementPanel({ achievements }: AchievementPanelProps) {
  const tg = useTranslations('gamification')
  const unlocked = achievements.filter(a => a.unlocked_at)
  const locked = achievements.filter(a => !a.unlocked_at)

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-400">
          <Medal className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-foreground-muted">{tg('achievements')}</p>
          <p className="text-lg font-bold text-foreground">{tg('unlocked_count', { unlocked: unlocked.length, total: achievements.length })}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {achievements.map(a => {
          const isUnlocked = !!a.unlocked_at
          const keys = ACHIEVEMENT_KEY_MAP[a.id]
          const title = keys ? tg(keys.title) : a.title
          const desc = keys ? tg(keys.desc) : a.description
          return (
            <div
              key={a.id}
              className={`relative flex flex-col items-center p-3 rounded-lg text-center transition-colors ${
                isUnlocked
                  ? 'bg-purple-500/10 border border-purple-500/20'
                  : 'bg-background-secondary/50 border border-border/50 opacity-50'
              }`}
            >
              {isUnlocked ? (
                <Medal className="w-6 h-6 text-purple-400 mb-1.5" />
              ) : (
                <Lock className="w-6 h-6 text-foreground-muted mb-1.5" />
              )}
              <p className="text-xs font-medium text-foreground">{title}</p>
              <p className="text-[10px] text-foreground-muted mt-0.5 leading-tight">{desc}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
