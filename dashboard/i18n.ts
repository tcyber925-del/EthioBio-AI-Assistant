import { getRequestConfig } from 'next-intl/server';

export default getRequestConfig(async ({ locale }) => {
  const lang = locale ?? 'en';
  return {
    locale: lang,
    messages: (await import(`./messages/${lang}.json`)).default,
  };
});
