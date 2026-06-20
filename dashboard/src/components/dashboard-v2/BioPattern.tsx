'use client'

import { DnaIcon } from './BioIcon'

export function BioPattern() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none select-none" aria-hidden="true">
      {/* DNA helix — left side */}
      <div className="absolute -left-20 top-1/4 w-64 h-96 opacity-[0.03]">
        <DnaIcon className="w-full h-full" />
      </div>

      {/* Cell circles — scattered */}
      <div className="absolute top-1/3 right-10 w-48 h-48 rounded-full border border-current opacity-[0.02] text-v2-accent" />
      <div className="absolute bottom-1/4 left-1/3 w-32 h-32 rounded-full border border-current opacity-[0.015] text-v2-accent" />

      {/* Grid dots — molecular motif */}
      <div className="absolute inset-0 opacity-[0.015]">
        <svg width="100%" height="100%" className="text-v2-accent">
          <defs>
            <pattern id="bio-dots" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
              <circle cx="20" cy="20" r="1" fill="currentColor" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#bio-dots)" />
        </svg>
      </div>
    </div>
  )
}
