import { test, expect } from '@playwright/test'

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'

test.describe('Login page', () => {
  test('renders sign-in controls (email, password, Google)', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`)
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /continue with google/i })).toBeVisible()
  })

  test('switches to the create-account form', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`)
    await page.getByRole('button', { name: /create account/i }).first().click()
    await expect(page.getByRole('button', { name: /create & sign in/i })).toBeVisible()
  })
})