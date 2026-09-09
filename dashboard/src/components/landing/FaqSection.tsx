import { getTranslations } from 'next-intl/server'
import { Accordion } from '@/components/ui/Accordion'

const FAQ_COUNT = 8

export default async function FaqSection() {
  const t = await getTranslations('landing')

  const items = Array.from({ length: FAQ_COUNT }, (_, i) => ({
    id: `faq-${i + 1}`,
    title: t(`faq_q${i + 1}`),
    content: t(`faq_a${i + 1}`),
  }))

  return (
    <section id="faq" className="border-b border-[#2d2d2d] py-20">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <h2 className="verge-display mb-10 text-center text-3xl text-white sm:text-4xl">
          {t('faq_title')}
        </h2>
        <Accordion
          items={items}
          className="border border-[#2d2d2d] bg-[#181818] px-4"
          dividerClassName="divide-[#2d2d2d]"
          itemTitleClassName="text-white"
          itemContentClassName="text-gray-400"
        />
      </div>
    </section>
  )
}