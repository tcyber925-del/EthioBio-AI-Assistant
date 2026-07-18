import createMiddleware from 'next-intl/middleware';

export default createMiddleware({
  locales: ['en', 'am'],
  defaultLocale: 'en',
  localeDetection: false,
  localePrefix: 'never',
});

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)'],
};
