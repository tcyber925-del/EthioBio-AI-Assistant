'use client'

import { motion } from 'framer-motion'
import { useTranslations } from 'next-intl'
import Link from 'next/link'
import { motion as motionTokens } from '@/styles/design-system'

const steps = [
  'hero_step_question',
  'hero_step_understand',
  'hero_step_retrieve',
  'hero_step_verify',
  'hero_step_explain',
  'hero_step_master',
] as const

const kickers = ['hero_label_1', 'hero_label_2', 'hero_label_3'] as const

const titleLines = ['hero_title_1', 'hero_title_2', 'hero_title_3'] as const

const rise = (delayMs: number) => ({
  initial: { opacity: 0, y: 40 },
  animate: { opacity: 1, y: 0 },
  transition: {
    duration: Number.parseInt(motionTokens.reveal, 10) / 1000,
    delay: delayMs / 1000,
    ease: motionTokens.revealEasing,
  },
})

export default function HeroSection() {
  const t = useTranslations('landing')

  return (
    <section id="top" className="relative overflow-hidden">
      <div aria-hidden className="sci-grid pointer-events-none absolute inset-0 opacity-40" />
      <div className="relative mx-auto grid max-w-[1280px] gap-12 px-5 pb-20 pt-14 md:px-8 lg:grid-cols-12 lg:pb-28 lg:pt-20">
        <div className="lg:col-span-7">
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            {kickers.map((key, i) => (
              <motion.p key={key} {...rise(i * 120)} className="label-mono text-meta">
                {t(key)}
              </motion.p>
            ))}
          </div>

          <h1 className="display mt-8 text-[54px] sm:text-[80px] lg:text-[104px]">
            {titleLines.map((key, i) => (
              <span key={key} className="block overflow-hidden">
                <motion.span
                  {...rise(300 + i * 140)}
                  className={`block ${i === 2 ? 'text-mint' : 'text-white'}`}
                >
                  {t(key)}
                </motion.span>
              </span>
            ))}
          </h1>

          <motion.p {...rise(800)} className="mt-8 max-w-xl text-lg text-soft">
            {t('hero_body')}
          </motion.p>

          <motion.div {...rise(1000)} className="mt-10 flex flex-wrap gap-3">
            <Link
              href="/sign-up?role=learner"
              className="label-mono inline-flex min-h-12 items-center rounded-stage bg-mint px-7 font-bold text-ink transition-colors hover:bg-white"
            >
              {t('hero_cta_start')} <span aria-hidden className="ml-2">→</span>
            </Link>
            <a
              href="#subjects"
              className="label-mono inline-flex min-h-12 items-center rounded-cta border border-white/40 px-7 text-white transition-colors hover:border-mint hover:text-mint"
            >
              {t('hero_cta_explore')}
            </a>
          </motion.div>
        </div>

        <div className="relative lg:col-span-5">
          <div className="relative aspect-square overflow-hidden rounded-feature border bg-ink">
            <img
              src="/landing/hero-dna.jpg"
              alt={t('hero_image_alt')}
              width={1280}
              height={1280}
              loading="eager"
              fetchPriority="high"
              className="absolute inset-0 h-full w-full object-cover opacity-45"
            />
            <svg viewBox="0 0 400 400" className="absolute inset-0 h-full w-full" aria-hidden>
              <circle
                cx="200"
                cy="200"
                r="170"
                fill="none"
                stroke="currentColor"
                className="anim-spin text-line"
                strokeDasharray="2 8"
              />
              {steps.map((_, i) => {
                if (i === steps.length - 1) return null
                const y1 = 45 + i * 62
                const y2 = 45 + (i + 1) * 62
                const x1 = i % 2 ? 250 : 150
                const x2 = (i + 1) % 2 ? 250 : 150
                return (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="currentColor"
                    strokeWidth="1.5"
                    className="anim-draw text-mint"
                    style={{ animationDelay: `${1200 + i * 220}ms` }}
                  />
                )
              })}
            </svg>
            <ol className="absolute inset-0">
              {steps.map((key, i) => (
                <motion.li
                  key={key}
                  {...rise(1100 + i * 220)}
                  className="absolute flex items-center gap-2"
                  style={{
                    top: `${((45 + i * 62) / 400) * 100}%`,
                    left: `${((i % 2 ? 250 : 150) / 400) * 100}%`,
                    translate: '-6px -50%',
                  }}
                >
                  <span
                    className={`size-3 rounded-full ${
                      i === 5 ? 'bg-violet ring-2 ring-mint' : 'bg-mint'
                    }`}
                  />
                  <span className="label-mono rounded-input bg-ink px-2 py-1 text-white">
                    <span aria-hidden>{String(i + 1).padStart(2, '0')}</span> {t(key)}
                  </span>
                </motion.li>
              ))}
            </ol>
            <p className="label-mono absolute bottom-4 left-4 text-mint">● Status / online</p>
            <p className="label-mono absolute right-4 top-4 text-meta">RAG / active</p>
          </div>
        </div>
      </div>
    </section>
  )
}
