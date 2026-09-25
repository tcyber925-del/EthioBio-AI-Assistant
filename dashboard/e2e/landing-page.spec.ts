import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

// Remote runs (BASE_URL pointed at a deployed origin) pay CDN/edge latency for
// lazy chunks and navigations; give assertions and test budgets room for it.
// Local runs keep the tight default budgets, so CI-equivalent runs stay strict.
const REMOTE = !/localhost|127\.0\.0\.1/.test(BASE_URL);
if (REMOTE) {
  test.expect.configure({ timeout: 15_000 });
}

test.describe('Landing Page', () => {
  if (REMOTE) test.slow();
  test('loads with the ported hero and primary CTA', async ({ page }) => {
    await page.goto(BASE_URL);
    const h1 = page.locator('h1');
    await expect(h1).toContainText('Science,');
    await expect(h1).toContainText('Ethiopia.');
    await expect(page.getByRole('link', { name: /start learning/i }).first()).toHaveAttribute(
      'href',
      '/sign-up?role=learner',
    );
    // Telegram survives in the footer; login lives in the footer portal column.
    await expect(page.locator('footer a[href="https://t.me/ethiobio_bot"]')).toBeVisible();
    await expect(page.locator('footer a[href="/login"]').first()).toBeVisible();
  });

  test('all ported sections render in order with their anchors', async ({ page }) => {
    await page.goto(BASE_URL);
    for (const id of ['learn', 'subjects', 'how', 'teachers', 'stats', 'faq']) {
      await expect(page.locator(`section[id="${id}"]`)).toHaveCount(1);
    }
    await expect(page.locator('#learn h2')).toContainText('Ask a science question');
    await expect(page.locator('#subjects h2')).toContainText('Four science worlds');
    await expect(page.locator('#how h2')).toContainText('learning pipeline');
    await expect(page.locator('#teachers')).toBeVisible();
    // The old console/features sections are gone.
    await expect(page.locator('#console')).toHaveCount(0);
    await expect(page.locator('#features')).toHaveCount(0);
  });

  test('header nav links to the in-page sections', async ({ page }) => {
    await page.goto(BASE_URL);
    const nav = page.locator('header nav');
    await expect(nav.locator('a[href="#learn"]')).toBeVisible();
    await expect(nav.locator('a[href="#subjects"]')).toBeVisible();
    await expect(nav.locator('a[href="#how"]')).toBeVisible();
    await expect(nav.locator('a[href="#teachers"]')).toBeVisible();
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

  test('role CTAs deep-link to role signup', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('a[href="/sign-up?role=learner"]').first()).toBeVisible();
    await expect(page.locator('a[href="/sign-up?role=teacher"]').first()).toBeVisible();
  });

  test('FAQ section renders questions and answers', async ({ page }) => {
    await page.goto(BASE_URL);
    const faq = page.locator('#faq');
    await expect(faq).toBeVisible();
    await expect(faq.getByRole('heading', { level: 2 })).toContainText('Frequently asked');
    await faq.getByRole('button', { name: /is ethiosci free/i }).click();
    await expect(faq.getByText(/free for learners/i)).toBeVisible();
  });

  test('quiz demo answers and gives feedback', async ({ page }) => {
    await page.goto(BASE_URL);
    const answer = page.getByRole('radio', { name: /DNA/ }).first();
    await answer.scrollIntoViewIfNeeded();
    await answer.click();
    await expect(page.getByText(/✓ Correct/i)).toBeVisible();
    await expect(page.getByText(/Streak \+1/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /try again/i })).toBeVisible();
  });

  test('language switcher toggles to Amharic', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('button:has-text("አማ")').click();
    await expect(page.locator('h1')).toContainText('ለኢትዮጵያ');
    await expect(page.getByText('ሳይንስን ተማር')).toBeVisible();
  });

  test('Start learning navigates to sign-up with role', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.getByRole('link', { name: /start learning/i }).first().click();
    await expect(page).toHaveURL(/\/sign-up\?role=learner/);
  });

  test('stats section shows live counts or an em dash, never placeholders', async ({ page }) => {
    await page.goto(BASE_URL);
    const stats = page.locator('#stats');
    await expect(stats).toBeVisible();
    // Values are digits (loaded) or an em dash (failed) — no fabricated defaults.
    await expect(stats.locator('span.display').first()).toHaveText(/^[\d, —]+$/);
  });

  test('footer has resources and portal links', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('footer')).toBeVisible();
    await expect(page.locator('footer a[href="/login"]').first()).toBeVisible();
    await expect(page.locator('footer a[href="#faq"]').first()).toBeVisible();
    await expect(page.locator('footer a[href="/v2/overview"]').first()).toBeVisible();
  });

  test('mobile viewport has no horizontal overflow at 390px', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(BASE_URL);
    // hydrate first, then assert the document never scrolls sideways
    await expect
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth),
      )
      .toBeLessThanOrEqual(0);
  });

  test('mobile hamburger opens the menu with links and language toggle', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(BASE_URL);
    await expect(page.getByRole('button', { name: 'Open menu' })).toBeVisible();
    await expect(page.locator('#mobile-menu')).toHaveCount(0);

    await page.getByRole('button', { name: 'Open menu' }).click();
    await expect(page.locator('#mobile-menu')).toBeVisible();
    await expect(
      page.locator('#mobile-menu').getByRole('link', { name: 'Learn' }),
    ).toBeVisible();
    // the language toggle lives inside the menu on mobile
    await expect(page.locator('#mobile-menu button:has-text("አማ")')).toBeVisible();

    await page.getByRole('button', { name: 'Close menu' }).click();
    await expect(page.locator('#mobile-menu')).toHaveCount(0);
  });

  test('stats loaded state renders figures and the live badge (mocked API)', async ({ page }) => {
    await page.route('**/auth/public-stats*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          active_students: 1284,
          quizzes_completed: 9312,
          lesson_plans_generated: 470,
          knowledge_assets: 156,
          system_status: 'ok',
        }),
      }),
    );
    await page.goto(BASE_URL);
    const stats = page.locator('#stats');
    await expect(stats.locator('span.display').first()).toHaveText('1,284');
    await expect(stats.getByText('Real-Time platform counts')).toBeVisible();
  });

  test('stats failure shows em dash and error line, never a live badge', async ({ page }) => {
    await page.route('**/auth/public-stats*', (route) =>
      route.fulfill({ status: 500, body: 'boom' }),
    );
    await page.goto(BASE_URL);
    const stats = page.locator('#stats');
    await expect(stats.locator('span.display').first()).toHaveText('—');
    await expect(stats.getByText('Live counts are unavailable right now.')).toBeVisible();
    // the "live" badge must never show when counts failed to load
    await expect(stats.getByText('Real-Time platform counts')).toHaveCount(0);
  });
});
