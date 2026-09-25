import { getTranslations } from 'next-intl/server'
import { Accordion } from '@/components/ui/Accordion'
import { Label } from './Reveal'

const FAQ_COUNT = 8

export default async function FaqSection() {
  const t = await getTranslations('landing')

  const items = Array.from({ length: FAQ_COUNT }, (_, i) => ({
    id: `faq-${i + 1}`,
    title: t(`faq_q${i + 1}`),
    content: t(`faq_a${i + 1}`),
  }))

  return (
    <section id="faq" className="border-t">
      <div className="mx-auto max-w-3xl px-5 py-24 md:px-8">
        <Label>{t('faq_kicker')}</Label>
        <h2 className="display mb-10 mt-6 text-[40px] text-white md:text-[56px]">
          {t('faq_title')}
        </h2>
        <Accordion
          items={items}
          className="border border-line bg-slate px-4"
          dividerClassName="divide-line"
          itemTitleClassName="text-white"
          itemContentClassName="text-soft"
        />
      </div>
    </section>
  )
}