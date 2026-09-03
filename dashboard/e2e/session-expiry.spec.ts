import { test, expect } from '@playwright/test'

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'

test.describe('Session expiry', () => {
  test('expired session redirects to /sign-in with next param', async ({ page }) => {
    // A stale Clerk session cookie lets the middleware through; the backend
    // then rejects the API call with 401, which should route to /sign-in.
    await page.context().addCookies([{ name: '__session', value: 'expired-clerk-jwt', url: BASE_URL }])
    await page.route('**/api/teacher/students', route =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'auth_token_expired', detail: 'x', context: {} } }),
      }),
    )
    await page.goto(`${BASE_URL}/students`)
    await expect(page).toHaveURL(/\/sign-in\?next=%2Fstudents/, { timeout: 15000 })
  })

  test('login page stays put (public route, no redirect loop)', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`)
    await expect(page).toHaveURL(/\/login$/)
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible()
  })
})