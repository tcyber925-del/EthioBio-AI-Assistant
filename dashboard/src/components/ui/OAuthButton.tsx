'use client'

import { forwardRef, type ButtonHTMLAttributes } from 'react'

export type OAuthProvider = 'google' | 'microsoft'

interface OAuthButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  provider: OAuthProvider
  label: string
  loading?: boolean
  compact?: boolean
}

const providerLabels: Record<OAuthProvider, string> = {
  google: 'Google',
  microsoft: 'Microsoft',
}

const OAuthButton = forwardRef<HTMLButtonElement, OAuthButtonProps>(
  (
    {
      provider,
      label,
      loading = false,
      compact = false,
      disabled,
      className = '',
      type = 'button',
      ...props
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        aria-label={label || `Continue with ${providerLabels[provider]}`}
        className={`inline-flex items-center justify-center gap-2 rounded-lg border border-v2-border bg-v2-surface font-medium text-v2-text-primary transition-all duration-150 hover:bg-v2-bg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-v2-focus disabled:cursor-not-allowed disabled:opacity-50 ${
          compact ? 'px-3 py-1.5 text-xs' : 'w-full px-4 py-2.5 text-sm'
        } ${className}`}
        {...props}
      >
        {loading ? (
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        ) : provider === 'google' ? (
          <GoogleIcon />
        ) : (
          <MicrosoftIcon />
        )}
        <span>{label}</span>
      </button>
    )
  },
)

OAuthButton.displayName = 'OAuthButton'

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"
      />
    </svg>
  )
}

function MicrosoftIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
      <path fill="#F25022" d="M1 1h7.5v7.5H1z" />
      <path fill="#00A4EF" d="M9.5 1H17v7.5H9.5z" />
      <path fill="#7FBA00" d="M1 9.5h7.5V17H1z" />
      <path fill="#FFB900" d="M9.5 9.5H17V17H9.5z" />
    </svg>
  )
}

export default OAuthButton
