'use client'

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: number | string
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'indigo' | 'teal' | 'red'
  subtitle?: string
}

const colors: Record<string, string> = {
  blue: 'bg-blue-50 text-blue-600',
  green: 'bg-green-50 text-green-600',
  purple: 'bg-purple-50 text-purple-600',
  orange: 'bg-orange-50 text-orange-600',
  indigo: 'bg-indigo-50 text-indigo-600',
  teal: 'bg-teal-50 text-teal-600',
  red: 'bg-red-50 text-red-600',
}

export default function StatCard({ icon, label, value, color = 'blue', subtitle }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${colors[color]}`}>{icon}</div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
    </div>
  )
}
