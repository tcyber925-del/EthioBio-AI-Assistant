'use client'

import { forwardRef, type SelectHTMLAttributes } from 'react'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  className?: string
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className = '', children, disabled, ...props }, ref) => {
    return (
      <div className={`relative inline-block w-full ${className}`}>
        <select
          ref={ref}
          disabled={disabled}
          className="w-full appearance-none rounded-lg border border-v2-border bg-v2-surface px-3 py-2 pr-9 text-sm text-v2-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus disabled:cursor-not-allowed disabled:opacity-50"
          {...props}
        >
          {children}
        </select>
        <span
          aria-hidden
          className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-v2-text-secondary"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
              d="M4 6l4 4 4-4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
      </div>
    )
  },
)

Select.displayName = 'Select'

export default Select
