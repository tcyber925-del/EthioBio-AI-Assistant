import { getTranslations } from 'next-intl/server'
import { Reveal, Label } from './Reveal'

/**
 * "02 / Subjects" — four subject tiles in a mosaic. Names come from the
 * canonical `subjectgrade` vocabulary; notes/alt text are landing copy.
 * Tiles link to the demo section (no per-subject route exists yet).
 */
const tiles = [
  {
    key: 'biology',
    nameKey: 'subject_biology',
    noteKey: 'subj_note_biology',
    altKey: 'subj_tile_biology_alt',
    sym: 'C₆H₁₂O₆',
    tone: 'bg-mint text-ink',
    span: 'md:col-span-7 md:row-span-2',
    titleSize: 'text-[64px] md:text-[96px]',
    img: '/landing/biology.jpg',
    imgClass: 'inset-0 h-full w-full',
  },
  {
    key: 'chemistry',
    nameKey: 'subject_chemistry',
    noteKey: 'subj_note_chemistry',
    altKey: 'subj_tile_chemistry_alt',
    sym: 'Na⁺ + Cl⁻',
    tone: 'bg-violet text-white',
    span: 'md:col-span-5',
    titleSize: 'text-[48px] md:text-[60px]',
    img: '/landing/chemistry.jpg',
    imgClass: 'inset-0 h-full w-full',
  },
  {
    key: 'physics',
    nameKey: 'subject_physics',
    noteKey: 'subj_note_physics',
    altKey: 'subj_tile_physics_alt',
    sym: 'F = ma',
    tone: 'bg-volt text-white',
    span: 'md:col-span-5',
    titleSize: 'text-[48px] md:text-[60px]',
    img: '/landing/physics.jpg',
    imgClass: 'inset-0 h-full w-full',
  },
  {
    key: 'mathematics',
    nameKey: 'subject_mathematics',
    noteKey: 'subj_note_mathematics',
    altKey: 'subj_tile_mathematics_alt',
    sym: 'a² + b² = c²',
    tone: 'bg-sun text-ink',
    span: 'md:col-span-12',
    titleSize: 'text-[48px] md:text-[60px]',
    img: '/landing/math.jpg',
    imgClass: 'inset-y-0 right-0 w-1/2',
  },
] as const

export default async function SubjectsSection() {
  const t = await getTranslations('landing')
  const tg = await getTranslations('subjectgrade')

  return (
    <section id="subjects" className="border-t">
      <div className="mx-auto max-w-[1280px] px-5 py-24 md:px-8">
        <Label>{t('subj_kicker')}</Label>
        <h2 className="display mt-6 text-[48px] md:text-[88px]">
          {t('subj_title_1')}
          <br />
          <span className="text-mint">{t('subj_title_2')}</span>
        </h2>

        <div className="mt-14 grid gap-4 md:grid-cols-12">
          {tiles.map((tile, i) => (
            <Reveal key={tile.key} delay={i * 100} className={tile.span}>
              <a
                href="#learn"
                className={`group relative flex h-full min-h-[320px] flex-col justify-between overflow-hidden rounded-feature ${tile.tone} ${
                  i === 3 ? 'md:flex-row md:items-end' : ''
                }`}
              >
                <img
                  src={tile.img}
                  alt={t(tile.altKey)}
                  loading="lazy"
                  width={1024}
                  height={1024}
                  className={`absolute object-cover opacity-40 mix-blend-luminosity transition-opacity duration-500 group-hover:opacity-70 ${tile.imgClass}`}
                />
                <div className="relative flex items-start justify-between p-6">
                  <p className="label-mono font-bold">
                    <span aria-hidden>{String(i + 1).padStart(2, '0')}</span> / {t('subj_tile_label')}
                  </p>
                  <p className="label-mono">{tile.sym}</p>
                </div>
                <div className="relative p-6">
                  <h3 className={`display ${tile.titleSize}`}>{tg(tile.nameKey)}</h3>
                  <p className="mt-2 max-w-xs font-medium">{t(tile.noteKey)}</p>
                  <p className="label-mono mt-5 inline-flex items-center gap-2 border-b border-current pb-1">
                    {t('subj_explore')} <span aria-hidden className="transition-transform group-hover:translate-x-1">→</span>
                  </p>
                </div>
              </a>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
