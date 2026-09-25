import { getTranslations } from 'next-intl/server'
import { Label, Reveal } from './Reveal'

/**
 * "10 / Learning stream" — a sample day of activity. Subject names come from
 * the canonical `subjectgrade` vocabulary; timestamps stay literal (format
 * notation); event copy and metrics are translated.
 */
const events = [
  { at: '09:42', subject: 'subject_biology', color: 'text-mint', text: 'stream_ev_1_text', metric: 'stream_ev_1_metric' },
  { at: '10:15', subject: 'subject_physics', color: 'text-volt', text: 'stream_ev_2_text', metric: 'stream_ev_2_metric' },
  { at: '11:03', subject: 'subject_chemistry', color: 'text-flame', text: 'stream_ev_3_text', metric: 'stream_ev_3_metric' },
] as const

export default async function StreamSection() {
  const t = await getTranslations('landing')
  const tg = await getTranslations('subjectgrade')

  return (
    <section className="border-t">
      <div className="mx-auto grid max-w-[1280px] gap-12 px-5 py-24 md:px-8 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <Label>{t('stream_kicker')}</Label>
          <h2 className="display mt-6 text-[48px] md:text-[72px]">{t('stream_title')}</h2>
        </div>

        <ol className="border-l lg:col-span-7">
          {events.map((ev, i) => (
            <li key={ev.at} className="relative border-b py-8 pl-8">
              <Reveal delay={i * 150}>
                <span className="absolute -left-[5px] top-10 size-[9px] rounded-full bg-mint" />
                <div className="flex gap-4">
                  <span className="label-mono text-meta">{ev.at}</span>
                  <span className={`label-mono ${ev.color}`}>{tg(ev.subject)}</span>
                </div>
                <p className="mt-3 text-2xl font-bold">{t(ev.text)}</p>
                <p className={`label-mono mt-2 ${ev.color}`}>{t(ev.metric)}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
