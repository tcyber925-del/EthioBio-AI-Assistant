import { getTranslations } from 'next-intl/server'
import { Label, Reveal } from './Reveal'

/**
 * "07 / 08 / For teachers & parents" — the two audience cards. Static: server
 * component (Reveal/Label are client leaves).
 */
const teacherWords = ['aud_word_plan', 'aud_word_assign', 'aud_word_review', 'aud_word_monitor'] as const
const teacherItems = ['aud_t_item_1', 'aud_t_item_2', 'aud_t_item_3', 'aud_t_item_4'] as const
const parentItems = ['aud_p_item_1', 'aud_p_item_2', 'aud_p_item_3'] as const

export default async function AudiencesSection() {
  const t = await getTranslations('landing')

  return (
    <section id="teachers" className="border-t">
      <div className="mx-auto grid max-w-[1280px] gap-4 px-5 py-24 md:px-8 lg:grid-cols-12">
        <Reveal className="lg:col-span-7">
          <article className="grid h-full overflow-hidden rounded-feature border md:grid-cols-2">
            <img
              src="/landing/teacher.jpg"
              alt={t('aud_teacher_alt')}
              loading="lazy"
              width={1024}
              height={1024}
              className="h-64 w-full object-cover md:h-full"
            />
            <div className="flex flex-col justify-between p-6 md:p-8">
              <div>
                <Label>{t('aud_kicker_teacher')}</Label>
                <p className="display mt-6 text-4xl leading-tight">
                  {teacherWords.map((key, i) => (
                    <span key={key} className="block">
                      {i === teacherWords.length - 1 ? (
                        <span className="text-mint">{t(key)}</span>
                      ) : (
                        t(key)
                      )}
                    </span>
                  ))}
                </p>
              </div>
              <ul className="mt-8 space-y-2 text-soft">
                {teacherItems.map((key) => (
                  <li key={key}>— {t(key)}</li>
                ))}
              </ul>
            </div>
          </article>
        </Reveal>

        <Reveal delay={120} className="lg:col-span-5">
          <article className="flex h-full flex-col overflow-hidden rounded-feature bg-mint text-ink">
            <img
              src="/landing/parent.jpg"
              alt={t('aud_parent_alt')}
              loading="lazy"
              width={1024}
              height={1024}
              className="h-56 w-full object-cover"
            />
            <div className="p-6 md:p-8">
              <p className="label-mono">{t('aud_kicker_parent')}</p>
              <p className="display mt-4 text-4xl">{t('aud_parent_words')}</p>
              <ul className="mt-6 space-y-2 font-medium">
                {parentItems.map((key) => (
                  <li key={key}>— {t(key)}</li>
                ))}
              </ul>
            </div>
          </article>
        </Reveal>
      </div>
    </section>
  )
}
