'use client'

export function BioPattern() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none select-none" aria-hidden="true">
      <div className="absolute left-0 top-0 h-full w-px bg-v2-purple-rule/70" />
      <div className="absolute inset-0 opacity-[0.035]">
        <svg width="100%" height="100%" className="text-v2-accent">
          <defs>
            <pattern id="editorial-dots" x="0" y="0" width="44" height="44" patternUnits="userSpaceOnUse">
              <circle cx="22" cy="22" r="1" fill="currentColor" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#editorial-dots)" />
        </svg>
      </div>

    </div>
  )
}
