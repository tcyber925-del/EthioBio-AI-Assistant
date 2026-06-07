import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { cookies } from 'next/headers';
import Sidebar from '@/components/Sidebar';
import './globals.css';

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'EthioBio AI Assistant',
  description: 'Personalized Biology Tutoring for Ethiopian Grades 7-12',
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const locale = cookieStore.get('NEXT_LOCALE')?.value ?? 'en';
  const messages = (await import(`../../messages/${locale}.json`)).default;

  return (
    <html lang={locale}>
      <body className="bg-background text-foreground font-sans">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 p-6 lg:p-8 overflow-auto">
              {children}
            </main>
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
