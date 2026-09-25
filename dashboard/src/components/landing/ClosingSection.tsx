import { getTranslations } from 'next-intl/server'
import Link from 'next/link'

/**
 * Final CTA — the page closes on the full-bleed mint band. Primary routes to
 * role-first sign-up (per the CTA decisions); the secondary goes to the
 * pipeline section. The global footer lives in the `(marketing)` layout, so
 * the source's in-section footer row is intentionally not ported.
 */
export default async function ClosingSection() {
  const t = await getTranslations('landing')

  return (
    <section className="bg-mint text-ink">
      <div className="mx-auto grid max-w-[1280px] gap-10 px-5 py-24 md:px-8 lg:grid-cols-12 lg:items-end">
        <h2 className="display text-[56px] md:text-[104px] lg:col-span-8">{t('cta_title')}</h2>
        <div className="lg:col-span-4">
          <p className="text-xl font-bold">{t('cta_sub')}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/sign-up?role=learner"
              className="label-mono inline-flex min-h-12 items-center rounded-stage bg-violet px-7 font-bold text-white transition-colors hover:bg-ink"
            >
              {t('hero_cta_start')} <span aria-hidden className="ml-2">→</span>
            </Link>
            <a
              href="#how"
              className="label-mono inline-flex min-h-12 items-center rounded-cta border-2 border-ink px-7 font-bold transition-colors hover:bg-ink hover:text-mint"
            >
              {t('cta_secondary')}
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
