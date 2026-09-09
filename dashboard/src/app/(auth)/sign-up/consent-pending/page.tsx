import Link from 'next/link'
import { getTranslations } from 'next-intl/server'

export default async function ConsentPendingPage() {
  const t = await getTranslations('signup')

  return (
    <div className="space-y-6 text-center">
      <h1 className="text-display text-2xl text-v2-text-primary">
        {t('consent_pending_title')}
      </h1>
      <p className="text-sm text-v2-text-secondary">{t('consent_pending_body')}</p>
      <Link href="/" className="inline-block text-sm font-medium text-v2-accent hover:text-v2-accent-hover">
        {t('back_home')}
      </Link>
    </div>
  )
}
