import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import Select from '../Select'

describe('Select', () => {
  it('renders options and fires onChange', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()

    render(
      <Select aria-label="Month" defaultValue="1" onChange={onChange}>
        <option value="1">January</option>
        <option value="2">February</option>
      </Select>,
    )

    const select = screen.getByRole('combobox', { name: 'Month' })
    expect(select).toHaveValue('1')

    await user.selectOptions(select, '2')
    expect(onChange).toHaveBeenCalled()
    expect(select).toHaveValue('2')
  })
})
