import { test, expect } from '@playwright/test'

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'

test.describe('Session expiry', () => {
  test('expired session redirects to /login with next param', async ({ page }) => {
    await page.context().addCookies([
      { name: 'access_token', value: 'expired', url: BASE_URL },
      // isAuthenticated() checks the auth_ready cookie, not access_token
      { name: 'auth_ready', value: '1', url: BASE_URL },
    ])
    await page.route('**/api/teacher/students', route =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'auth_token_expired', detail: 'x', context: {} } }),
      }),
    )
    await page.route('**/auth/refresh', route =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'auth_refresh_expired', detail: 'x', context: {} } }),
      }),
    )
    await page.goto(`${BASE_URL}/students`)
    await expect(page).toHaveURL(/\/login\?next=%2Fstudents/, { timeout: 15000 })
  })

  test('no redirect loop when already on /login', async ({ page }) => {
    await page.context().addCookies([{ name: 'access_token', value: 'expired', url: BASE_URL }])
    await page.route('**/auth/token*', route =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'auth_invalid_credentials', detail: 'x', context: {} },
        }),
      }),
    )
    await page.goto(`${BASE_URL}/login`)
    await page.fill('input[type="email"]', 'a@b.c')
    await page.fill('input[type="password"]', 'wrong-pass')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL(/\/login$/)
  })
})