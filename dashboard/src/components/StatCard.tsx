'use client'

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: number | string
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'indigo' | 'teal' | 'red'
  subtitle?: string
}

const colors: Record<string, { bg: string; text: string }> = {
  blue: { bg: 'bg-blue-500/10', text: 'text-blue-400' },
  green: { bg: 'bg-green-500/10', text: 'text-green-400' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-400' },
  orange: { bg: 'bg-orange-500/10', text: 'text-orange-400' },
  indigo: { bg: 'bg-indigo-500/10', text: 'text-indigo-400' },
  teal: { bg: 'bg-teal-500/10', text: 'text-teal-400' },
  red: { bg: 'bg-red-500/10', text: 'text-red-400' },
}

export default function StatCard({ icon, label, value, color = 'blue', subtitle }: StatCardProps) {
  const c = colors[color]
  return (
    <div className="bg-card rounded-xl border border-border p-5 hover:border-border/80 transition-colors">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${c.bg} ${c.text}`}>{icon}</div>
        <div>
          <p className="text-sm text-foreground-muted">{label}</p>
          <p className="text-2xl font-bold text-foreground">{value}</p>
          {subtitle && <p className="text-xs text-foreground-muted/60 mt-0.5">{subtitle}</p>}
        </div>
      </div>
    </div>
  )
}
