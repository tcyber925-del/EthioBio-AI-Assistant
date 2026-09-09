import { render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it } from 'vitest'
import FormField from '../FormField'

const messages = {
  errors: {
    validation: {
      missing: 'Please fill in the {field} field.',
    },
  },
}

describe('FormField', () => {
  it('shows required marker and wires FieldError', () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <FormField
          label="Email"
          htmlFor="email"
          required
          errorId="email-error"
          errorField="email"
          errorMessages={['errors.validation.missing']}
        >
          <input id="email" aria-describedby="email-error" />
        </FormField>
      </NextIntlClientProvider>,
    )

    expect(screen.getByText('*')).toBeInTheDocument()
    expect(screen.getByText('(required)')).toBeInTheDocument()
    expect(
      screen.getByText('Please fill in the email field.'),
    ).toBeInTheDocument()
  })
})
