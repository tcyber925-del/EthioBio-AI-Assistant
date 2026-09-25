'use client'

import { useTranslations } from 'next-intl'
import { useInView } from '@/hooks/useInView'
import { Label } from './Reveal'

/**
 * "05 / Student journey" — seven steps along a rule that draws itself on
 * scroll (CSS transition on width/height, driven by the in-view state).
 */
const stepKeys = [
  'journ_step_1',
  'journ_step_2',
  'journ_step_3',
  'journ_step_4',
  'journ_step_5',
  'journ_step_6',
  'journ_step_7',
] as const

const descKeys = [
  'journ_desc_1',
  'journ_desc_2',
  'journ_desc_3',
  'journ_desc_4',
  'journ_desc_5',
  'journ_desc_6',
  'journ_desc_7',
] as const

export default function JourneySection() {
  const t = useTranslations('landing')
  const { ref, inView } = useInView<HTMLDivElement>(0.3)

  return (
    <section className="border-t">
      <div className="mx-auto max-w-[1280px] px-5 py-24 md:px-8">
        <Label>{t('journ_kicker')}</Label>
        <h2 className="display mt-6 text-[48px] md:text-[80px]">{t('journ_title')}</h2>

        <div ref={ref} className="relative mt-16">
          <div className="absolute left-[7px] top-0 h-full w-px bg-line md:left-0 md:top-[7px] md:h-px md:w-full" />
          <div
            className="absolute left-[7px] top-0 w-px bg-mint transition-all duration-[2000ms] ease-out md:hidden"
            style={{ height: inView ? '100%' : 0 }}
          />
          <div
            className="absolute left-0 top-[7px] hidden h-px bg-mint transition-all duration-[2000ms] ease-out md:block"
            style={{ width: inView ? '100%' : 0 }}
          />
          <ol className="relative grid gap-8 md:grid-cols-7 md:gap-4">
            {stepKeys.map((key, i) => (
              <li key={key} className="flex gap-4 md:flex-col">
                <span
                  className={`size-[15px] shrink-0 rounded-full border-2 transition-colors duration-300 ${
                    inView ? 'border-mint bg-mint' : 'border-meta bg-ink'
                  }`}
                  style={{ transitionDelay: `${i * 280}ms` }}
                />
                <div>
                  <p className="display text-2xl md:text-3xl">{t(key)}</p>
                  <p className="label-mono mt-2 text-meta">{t(descKeys[i])}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}
