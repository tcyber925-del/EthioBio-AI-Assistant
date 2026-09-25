import { getTranslations } from 'next-intl/server'
import { Label, Reveal } from './Reveal'

/**
 * "09 / Lang / EN + AM" — the bilingual product statement: English display
 * line over the Amharic line in Ethiopic mint. Both strings are one designed
 * pair (`amh_learn_en` + `amh_learn_am`) so they are translated together; the
 * kicker is mono notation and stays literal in both locales.
 */
export default async function AmharicSection() {
  const t = await getTranslations('landing')

  return (
    <section className="border-t">
      <div className="mx-auto max-w-[1280px] px-5 py-24 md:px-8">
        <Label>09 / Lang / EN + AM</Label>
        <Reveal>
          <p className="display mt-10 text-[56px] md:text-[120px]">{t('amh_learn_en')}</p>
          <p lang="am" className="mt-2 font-ethiopic text-[52px] font-black leading-none text-mint md:text-[112px]">
            {t('amh_learn_am')}
          </p>
        </Reveal>
        <p className="mt-10 max-w-lg text-soft">{t('amh_body')}</p>
      </div>
    </section>
  )
}
