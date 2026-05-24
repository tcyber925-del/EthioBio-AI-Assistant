'use client'

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

export default function AchievementPanel({ achievements }: AchievementPanelProps) {
  const unlocked = achievements.filter(a => a.unlocked_at)
  const locked = achievements.filter(a => !a.unlocked_at)

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 rounded-lg bg-purple-500/10 text-purple-400">
          <Medal className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-foreground-muted">Achievements</p>
          <p className="text-lg font-bold text-foreground">{unlocked.length} / {achievements.length} unlocked</p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {achievements.map(a => {
          const isUnlocked = !!a.unlocked_at
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
              <p className="text-xs font-medium text-foreground">{a.title}</p>
              <p className="text-[10px] text-foreground-muted mt-0.5 leading-tight">{a.description}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
