'use client'

import { useId, type ReactNode } from 'react'
import { FieldError } from '@/components/ui/errors/FieldError'

interface FormFieldProps {
  label: string
  children: ReactNode
  required?: boolean
  requiredMarker?: string
  errorId?: string
  errorField?: string
  errorMessages?: string[]
  htmlFor?: string
  className?: string
  hint?: ReactNode
}

export function FormField({
  label,
  children,
  required = false,
  requiredMarker = '*',
  errorId,
  errorField,
  errorMessages = [],
  htmlFor,
  className = '',
  hint,
}: FormFieldProps) {
  const autoErrorId = useId()
  const resolvedErrorId = errorId ?? (errorMessages.length ? autoErrorId : undefined)
  const hasErrors = errorMessages.length > 0

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label
        htmlFor={htmlFor}
        className="text-sm font-medium text-v2-text-primary"
      >
        {label}
        {required && (
          <span className="ml-0.5 text-v2-error" aria-hidden>
            {requiredMarker}
          </span>
        )}
        {required && <span className="sr-only"> (required)</span>}
      </label>
      {children}
      {hint != null && !hasErrors && (
        <span className="text-xs text-v2-text-secondary">{hint}</span>
      )}
      {hasErrors && errorField && resolvedErrorId && (
        <FieldError
          id={resolvedErrorId}
          field={errorField}
          messages={errorMessages}
        />
      )}
    </div>
  )
}

export default FormField
