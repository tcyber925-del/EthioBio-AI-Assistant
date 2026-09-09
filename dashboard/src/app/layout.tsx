import { ClerkProvider } from '@clerk/nextjs';
import type { Metadata } from 'next';
import { Inter, JetBrains_Mono, Noto_Sans_Ethiopic, Spectral } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages } from 'next-intl/server';
import './globals.css';

export const dynamic = 'force-dynamic';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const spectral = Spectral({
  subsets: ['latin'],
  weight: ['400', '600', '700'],
  variable: '--font-spectral',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jbmono',
  display: 'swap',
});

const notoSansEthiopic = Noto_Sans_Ethiopic({
  subsets: ['ethiopic'],
  variable: '--font-ethiopic',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'EthioSci',
  description: 'Personalized Science Tutoring for Ethiopian Grades 7-12',
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html
      lang={locale}
      className={`${inter.variable} ${spectral.variable} ${jetbrainsMono.variable} ${notoSansEthiopic.variable}`}
    >
      <body className="bg-v2-bg text-v2-text-primary font-sans">
        <ClerkProvider>
          <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
          </NextIntlClientProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
