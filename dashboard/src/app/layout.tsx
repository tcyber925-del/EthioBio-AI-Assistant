import type { Metadata } from 'next';
import NextDynamic from 'next/dynamic';
import { NextIntlClientProvider } from 'next-intl';
import { cookies, headers } from 'next/headers';
import { BioPattern } from '@/components/dashboard-v2/BioPattern';
import './globals.css';

const SidebarV2 = NextDynamic(() => import('@/components/dashboard-v2/SidebarV2').then(m => m.SidebarV2), { ssr: false });

export const dynamic = 'force-dynamic';

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

  const headersList = await headers();
  const pathname = headersList.get('x-pathname') || '';
  const isV2 = pathname.startsWith('/v2');

  return (
    <html lang={locale}>
      <body className="bg-v2-bg text-v2-text-primary font-sans">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <div className="flex h-screen overflow-hidden">
            <SidebarV2 />
            <div className="relative flex flex-1 flex-col overflow-hidden min-w-0">
              <BioPattern />
              <div className={`relative z-10 flex-1 overflow-auto${isV2 ? '' : ' p-6 lg:p-8'}`}>
                {children}
              </div>
            </div>
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
