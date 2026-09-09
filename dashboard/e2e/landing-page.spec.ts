import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('Landing Page', () => {
  test('loads and displays hero section', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('h1')).toContainText('Science Learning for Ethiopian');
    await expect(page.getByRole('link', { name: /start learning/i })).toHaveAttribute(
      'href',
      '/sign-up?role=learner',
    );
    await expect(page.getByRole('link', { name: /try on telegram/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /log in/i }).first()).toBeVisible();
  });

  test('teacher banner links to teacher signup and dismisses', async ({ page }) => {
    await page.goto(BASE_URL);
    const banner = page.getByRole('link', { name: /sign up free/i });
    await expect(banner).toHaveAttribute('href', '/sign-up?role=teacher');
    await page.getByRole('button', { name: /dismiss banner/i }).click();
    await expect(page.getByRole('link', { name: /sign up free/i })).toHaveCount(0);
    await page.reload();
    await expect(page.getByRole('link', { name: /sign up free/i })).toHaveCount(0);
  });

  test('role panels deep-link to role signup', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('a[href="/sign-up?role=learner"]').first()).toBeVisible();
    await expect(page.locator('a[href="/sign-up?role=teacher"]').first()).toBeVisible();
    await expect(page.locator('a[href="/sign-up?role=parent"]').first()).toBeVisible();
  });

  test('FAQ section renders questions and answers', async ({ page }) => {
    await page.goto(BASE_URL);
    const faq = page.locator('#faq');
    await expect(faq).toBeVisible();
    await expect(faq.getByRole('heading', { level: 2 })).toContainText('Frequently asked');
    await faq.getByRole('button', { name: /is ethiosci free/i }).click();
    await expect(faq.getByText(/free for learners/i)).toBeVisible();
  });

  test('language switcher toggles to Amharic', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('button:has-text("አማ")').click();
    await expect(page.locator('text=የሳይንስ ትምህርት')).toBeVisible();
  });

  test('Start learning navigates to sign-up with role', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.getByRole('link', { name: /start learning/i }).first().click();
    await expect(page).toHaveURL(/\/sign-up\?role=learner/);
  });

  test('footer has resources and portal links', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('footer')).toBeVisible();
    await expect(page.locator('footer a[href="/login"]').first()).toBeVisible();
    await expect(page.locator('footer a[href="#faq"]').first()).toBeVisible();
    await expect(page.locator('footer a[href="/v2/overview"]').first()).toBeVisible();
  });
});