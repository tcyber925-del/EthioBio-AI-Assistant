import { getTranslations } from 'next-intl/server'
import { Label, Reveal } from './Reveal'

/**
 * "04 / Grounded learning" — the evidence chain beside the textbook photo.
 * Static content: server component (Reveal/Label are client leaves).
 */
const chainKeys = [
  'trust_chain_1',
  'trust_chain_2',
  'trust_chain_3',
  'trust_chain_4',
  'trust_chain_5',
] as const

export default async function TrustSection() {
  const t = await getTranslations('landing')

  return (
    <section className="border-t">
      <div className="mx-auto grid max-w-[1280px] gap-12 px-5 py-24 md:px-8 lg:grid-cols-12">
        <div className="lg:col-span-6">
          <Label>{t('trust_kicker')}</Label>
          <h2 className="display mt-6 text-[48px] md:text-[80px]">{t('trust_title')}</h2>

          <ol className="mt-10 space-y-0 border-l border-mint">
            {chainKeys.map((key, i) => (
              <li key={key} className="pl-6">
                <Reveal delay={i * 120} className="flex items-center gap-4 py-3">
                  <span className="label-mono text-mint">{String(i + 1).padStart(2, '0')}</span>
                  <span className="text-xl font-medium">{t(key)}</span>
                </Reveal>
              </li>
            ))}
          </ol>

          <div className="mt-10 inline-block rounded-micro bg-mint px-5 py-4 text-ink">
            <p className="label-mono">{t('trust_cites_label')}</p>
            <p className="mt-1 font-mono text-lg font-bold">{t('trust_citation')}</p>
          </div>
        </div>

        <Reveal className="lg:col-span-6">
          <figure className="overflow-hidden rounded-feature border">
            <img
              src="/landing/textbook.jpg"
              alt={t('trust_image_alt')}
              loading="lazy"
              width={1280}
              height={896}
              className="w-full object-cover"
            />
            <figcaption className="label-mono flex justify-between border-t bg-slate p-4 text-meta">
              <span>{t('trust_caption_1')}</span>
              <span>{t('trust_caption_2')}</span>
            </figcaption>
          </figure>
        </Reveal>
      </div>
    </section>
  )
}
