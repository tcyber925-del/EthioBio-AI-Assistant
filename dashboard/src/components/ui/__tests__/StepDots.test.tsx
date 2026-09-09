import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import StepDots from '../StepDots'

describe('StepDots', () => {
  it('exposes current step via progressbar semantics', () => {
    render(<StepDots current={2} total={4} />)

    const bar = screen.getByRole('progressbar', { name: 'Step 2 of 4' })
    expect(bar).toHaveAttribute('aria-valuenow', '2')
    expect(bar).toHaveAttribute('aria-valuemin', '1')
    expect(bar).toHaveAttribute('aria-valuemax', '4')
  })

  it('accepts a custom label', () => {
    render(<StepDots current={1} total={3} label="Signup progress" />)
    expect(
      screen.getByRole('progressbar', { name: 'Signup progress' }),
    ).toBeInTheDocument()
  })
})
