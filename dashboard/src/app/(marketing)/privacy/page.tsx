import type { Metadata } from 'next'
import { getTranslations } from 'next-intl/server'

export const metadata: Metadata = {
  title: 'Privacy Policy — EthioSci',
  robots: { index: false, follow: false },
}

export default async function PrivacyPage() {
  const t = await getTranslations('legal')

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
      <h1 className="verge-display mb-2 text-3xl font-black text-white">{t('privacy_title')}</h1>
      <p className="mb-8 font-mono text-xs text-gray-500">{t('privacy_updated')}</p>
      <p className="text-sm leading-relaxed text-gray-400">{t('privacy_body')}</p>
    </div>
  )
}