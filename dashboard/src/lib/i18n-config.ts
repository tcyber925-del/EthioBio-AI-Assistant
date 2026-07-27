/**
 * Isomorphic i18n constants — safe to import from both client components
 * and server code (unlike the root i18n.ts, which is server-only).
 */
export const LOCALES = ["en", "am"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "en";
export const LOCALE_COOKIE = "NEXT_LOCALE";

export function isLocale(value: string | undefined | null): value is Locale {
  return (LOCALES as readonly string[]).includes(value ?? "");
}
