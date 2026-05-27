import { test, expect } from '@playwright/test'

test.describe('Recovery Dashboard Visualizations', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/recovery')
  })

  test('shows empty state initially', async ({ page }) => {
    await expect(page.getByText('Enter a student ID to get started')).toBeVisible()
  })

  test('radar chart appears after loading student data', async ({ page }) => {
    const input = page.getByPlaceholder('Enter student UUID...')
    await input.fill('test-student-id')
    await page.getByRole('button', { name: 'Look up' }).click()
    await page.waitForResponse(response =>
      response.url().includes('/recovery/dashboard/') && response.status() === 200
    )
    await page.waitForTimeout(1000)
    const rechartsContainer = page.locator('.recharts-wrapper')
    await expect(rechartsContainer.first()).toBeVisible({ timeout: 5000 })
  })

  test('learning tree shows expandable topic nodes', async ({ page }) => {
    const input = page.getByPlaceholder('Enter student UUID...')
    await input.fill('test-student-id')
    await page.getByRole('button', { name: 'Look up' }).click()
    await page.waitForResponse(response =>
      response.url().includes('/recovery/dashboard/') && response.status() === 200
    )
    const expandButtons = page.locator('button').filter({ has: page.locator('svg.lucide-chevron-right') })
    if (await expandButtons.count() > 0) {
      await expandButtons.first().click()
      await expect(page.getByText('Attempts').first()).toBeVisible({ timeout: 3000 })
    }
  })

  test('heatmap renders with activity data', async ({ page }) => {
    const input = page.getByPlaceholder('Enter student UUID...')
    await input.fill('test-student-id')
    await page.getByRole('button', { name: 'Look up' }).click()
    await page.waitForResponse(response =>
      response.url().includes('/recovery/dashboard/') && response.status() === 200
    )
    await expect(page.getByText('Progress Heatmap')).toBeVisible({ timeout: 5000 })
  })
})
