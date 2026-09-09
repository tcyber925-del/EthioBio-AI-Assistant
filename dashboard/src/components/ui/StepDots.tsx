'use client'

interface StepDotsProps {
  current: number
  total: number
  label?: string
  className?: string
}

export function StepDots({
  current,
  total,
  label,
  className = '',
}: StepDotsProps) {
  const safeTotal = Math.max(0, total)
  const clamped = Math.min(Math.max(current, 1), Math.max(safeTotal, 1))
  const ariaLabel =
    label ?? `Step ${clamped} of ${safeTotal}`

  return (
    <div
      role="progressbar"
      aria-valuemin={1}
      aria-valuemax={safeTotal || 1}
      aria-valuenow={clamped}
      aria-label={ariaLabel}
      className={`flex items-center justify-center gap-2 ${className}`}
    >
      {Array.from({ length: safeTotal }, (_, index) => {
        const step = index + 1
        const active = step === clamped
        const completed = step < clamped
        return (
          <span
            key={step}
            aria-hidden
            className={`h-2 w-2 rounded-full transition-colors duration-150 ${
              active
                ? 'bg-v2-accent scale-110'
                : completed
                  ? 'bg-v2-accent/50'
                  : 'bg-v2-border'
            }`}
          />
        )
      })}
    </div>
  )
}

export default StepDots
