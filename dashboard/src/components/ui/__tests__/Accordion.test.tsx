import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import Accordion from '../Accordion'

describe('Accordion', () => {
  it('expands and collapses an item with aria-expanded', async () => {
    const user = userEvent.setup()
    render(
      <Accordion
        items={[
          { id: 'a', title: 'Question A', content: 'Answer A' },
          { id: 'b', title: 'Question B', content: 'Answer B' },
        ]}
      />,
    )

    const buttonA = screen.getByRole('button', { name: /Question A/i })
    expect(buttonA).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Answer A')).not.toBeInTheDocument()

    await user.click(buttonA)
    expect(buttonA).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Answer A')).toBeInTheDocument()

    await user.click(buttonA)
    expect(buttonA).toHaveAttribute('aria-expanded', 'false')
    await waitFor(() => {
      expect(screen.queryByText('Answer A')).not.toBeInTheDocument()
    })
  })

  it('keeps only one panel open by default', async () => {
    const user = userEvent.setup()
    render(
      <Accordion
        items={[
          { id: 'a', title: 'Question A', content: 'Answer A' },
          { id: 'b', title: 'Question B', content: 'Answer B' },
        ]}
      />,
    )

    const buttonA = screen.getByRole('button', { name: /Question A/i })
    const buttonB = screen.getByRole('button', { name: /Question B/i })

    await user.click(buttonA)
    await user.click(buttonB)

    expect(buttonA).toHaveAttribute('aria-expanded', 'false')
    expect(buttonB).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Answer B')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText('Answer A')).not.toBeInTheDocument()
    })
  })
})
