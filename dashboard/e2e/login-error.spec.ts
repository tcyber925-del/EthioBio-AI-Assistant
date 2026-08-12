import { test, expect } from '@playwright/test'

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'

test.describe('Login error handling', () => {
  test('invalid credentials show a translated error, not raw backend text', async ({ page }) => {
    await page.route('**/auth/token*', route =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'auth_invalid_credentials', detail: 'Invalid email or password', context: {} },
        }),
      }),
    )
    await page.goto(`${BASE_URL}/login`)
    await page.fill('input[type="email"]', 'a@b.c')
    await page.fill('input[type="password"]', 'wrong-pass')
    await page.click('button[type="submit"]')
    await expect(
      page.getByText(/Invalid email or password\. Please check your credentials and try again/),
    ).toBeVisible()
    await expect(page.getByText('[object Object]')).toBeHidden()
  })

  test('successful login navigates to the dashboard', async ({ page }) => {
    await page.route('**/auth/token*', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'set-cookie': 'access_token=dummy-token;Path=/;HttpOnly' },
        body: JSON.stringify({
          access_token: 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwicm9sZSI6InRlYWNoZXIifQ.x',
        }),
      }),
    )
    await page.goto(`${BASE_URL}/login`)
    await page.fill('input[type="email"]', 'a@b.c')
    await page.fill('input[type="password"]', 'right-pass')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/classroom/, { timeout: 15000 })
  })
})