import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('Landing Page', () => {
  test('loads and displays hero section', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('h1')).toContainText('Biology Learning, Accelerated by AI');
    await expect(page.locator('text=ETHIOPIAN CURRICULUM GRADES 7-12')).toBeVisible();
    await expect(page.locator('text=Launch App').first()).toBeVisible();
    await expect(page.locator('text=Try on Telegram')).toBeVisible();
  });

  test('navigation links work', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('text=Features')).toBeVisible();
    await expect(page.locator('text=Interactive Demo').first()).toBeVisible();
    await expect(page.locator('text=Numbers')).toBeVisible();
  });

  test('language switcher toggles to Amharic', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('button:has-text("አማ")').click();
    await expect(page.locator('text=የባዮሎጂ ትምህርት፣ በሰው ሰራሽ አስተዋይነት የዳበረ')).toBeVisible();
  });

  test('Launch App navigates to login', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('a[href="/login"]').first().click();
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('text=Sign In')).toBeVisible();
  });

  test('login page has email and password fields', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('text=Sign In')).toBeVisible();
  });

  test('interactive demo section has sample queries', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('a[href="#console"]').first().click();
    await expect(page.locator('text=What is the difference between prokaryotic and eukaryotic cells?')).toBeVisible();
    await expect(page.locator('text=Explain the main stages of cellular respiration.')).toBeVisible();
    await expect(page.locator('text=How does natural selection drive biological evolution?')).toBeVisible();
  });

  test('footer has resources and portal links', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('footer')).toBeVisible();
    await expect(page.locator('footer a[href="/login"]')).toBeVisible();
    await expect(page.locator('footer a[href="/v2/overview"]')).toBeVisible();
  });
});