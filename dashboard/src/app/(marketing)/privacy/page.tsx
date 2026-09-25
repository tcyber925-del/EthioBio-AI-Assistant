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
      <h1 className="display mb-2 text-4xl text-white md:text-5xl">{t('privacy_title')}</h1>
      <p className="label-mono mb-8 text-meta">{t('privacy_updated')}</p>
      <p className="max-w-[70ch] text-sm leading-relaxed text-soft">{t('privacy_body')}</p>
    </div>
  )
}