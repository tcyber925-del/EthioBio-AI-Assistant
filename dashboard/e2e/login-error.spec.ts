import { test, expect } from '@playwright/test'

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'

test.describe('Login page', () => {
  test('renders sign-in controls (email, password, Google, Microsoft)', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`)
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /continue with google/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /continue with microsoft/i })).toBeVisible()
  })

  test('links to password recovery and sign-up', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`)
    await expect(page.getByRole('link', { name: /forgot password/i })).toHaveAttribute(
      'href',
      '/forgot-password',
    )
    await expect(page.getByRole('link', { name: /create an account/i })).toHaveAttribute(
      'href',
      '/sign-up',
    )
  })

  test('does not expose register/claim UI (sign-in only)', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`)
    await expect(page.getByRole('button', { name: /create & sign in/i })).toHaveCount(0)
    await expect(page.getByText(/register as/i)).toHaveCount(0)
  })

  test('forgot-password page renders the email step', async ({ page }) => {
    await page.goto(`${BASE_URL}/forgot-password`)
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.getByRole('button', { name: /send code/i })).toBeVisible()
  })
})