import { getRequestConfig } from 'next-intl/server';
import { cookies } from 'next/headers';
import { deepMergeMessages } from '@/lib/i18n-merge';
import { DEFAULT_LOCALE, LOCALE_COOKIE, isLocale, type Locale } from '@/lib/i18n-config';

/**
 * Single locale resolver for the whole app.
 * Locale comes from the NEXT_LOCALE cookie (set by the language switcher);
 * unknown/missing values fall back to English. Non-default locales are
 * deep-merged over English so untranslated keys degrade to English text
 * instead of rendering raw message keys.
 */
export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const raw = cookieStore.get(LOCALE_COOKIE)?.value;
  const locale: Locale = isLocale(raw) ? raw : DEFAULT_LOCALE;

  const en = (await import('./messages/en.json')).default;
  const messages =
    locale === DEFAULT_LOCALE
      ? en
      : deepMergeMessages(en, (await import(`./messages/${locale}.json`)).default);

  return { locale, messages };
});
