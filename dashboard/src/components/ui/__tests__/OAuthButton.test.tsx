import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import OAuthButton from '../OAuthButton'

describe('OAuthButton', () => {
  it('renders Google and Microsoft variants with labels', () => {
    const { rerender } = render(
      <OAuthButton provider="google" label="Continue with Google" />,
    )
    expect(
      screen.getByRole('button', { name: 'Continue with Google' }),
    ).toBeInTheDocument()

    rerender(
      <OAuthButton provider="microsoft" label="Continue with Microsoft" />,
    )
    expect(
      screen.getByRole('button', { name: 'Continue with Microsoft' }),
    ).toBeInTheDocument()
  })

  it('calls onClick and shows loading state', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()
    const { rerender } = render(
      <OAuthButton
        provider="google"
        label="Continue with Google"
        onClick={onClick}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Continue with Google' }))
    expect(onClick).toHaveBeenCalledTimes(1)

    rerender(
      <OAuthButton
        provider="google"
        label="Continue with Google"
        loading
      />,
    )
    expect(screen.getByRole('button')).toBeDisabled()
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true')
  })
})
