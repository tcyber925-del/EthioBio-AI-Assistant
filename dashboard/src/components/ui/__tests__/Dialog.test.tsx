import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import Dialog from '../Dialog'

describe('Dialog', () => {
  it('renders when open and closes on Escape', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    render(
      <Dialog open onClose={onClose} title="Confirm">
        <p>Are you sure?</p>
        <button type="button">OK</button>
      </Dialog>,
    )

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Are you sure?')).toBeInTheDocument()

    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does not render when closed', () => {
    render(
      <Dialog open={false} onClose={() => undefined} title="Hidden">
        Secret
      </Dialog>,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
