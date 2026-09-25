'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslations } from 'next-intl'
import { motion as motionTokens } from '@/styles/design-system'
import { Label, Reveal } from './Reveal'

/**
 * "06 / Try a quiz" — a mocked adaptive-quiz card on the violet band. One
 * question is answerable (A is correct, C is the designed wrong path); the
 * result row rises in with framer-motion instead of the source's CSS keyframe.
 * Client-side only: no API call, per the design brief.
 */
const options: [string, string][] = [
  ['A', 'DNA'],
  ['B', 'ATP'],
  ['C', 'Glucose'],
  ['D', 'Protein'],
]

export default function QuizDemoSection() {
  const t = useTranslations('landing')
  const [pick, setPick] = useState<string | null>(null)
  const correct = pick === 'A'
  const xp = pick ? (correct ? 120 : 20) : 0

  return (
    <section className="border-t bg-violet">
      <div className="mx-auto grid max-w-[1280px] gap-12 px-5 py-24 md:px-8 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <p className="label-mono text-white/70">{t('quiz_kicker')}</p>
          <h2 className="display mt-6 text-[48px] md:text-[80px]">{t('quiz_title')}</h2>
          <p className="mt-6 max-w-sm text-white/85">{t('quiz_desc')}</p>
        </div>

        <Reveal className="lg:col-span-7">
          <div className="rounded-feature bg-ink p-6 md:p-8">
            <div className="flex items-center justify-between">
              <Label>{t('quiz_label')}</Label>
              <p
                className={`label-mono font-bold transition-colors ${pick ? 'text-mint' : 'text-meta'}`}
                aria-live="polite"
              >
                +{xp} XP
              </p>
            </div>

            <div className="mt-4 h-1 w-full rounded-full bg-slate">
              <div
                className="h-full rounded-full bg-mint transition-all duration-700"
                style={{ width: pick ? '40%' : '20%' }}
              />
            </div>
            <p className="label-mono mt-2 text-meta">
              {pick ? t('quiz_progress_2') : t('quiz_progress_1')}
            </p>

            <h3 className="mt-6 text-2xl font-bold md:text-3xl">{t('quiz_question')}</h3>

            <div className="mt-6 grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label={t('quiz_group_label')}>
              {options.map(([k, v]) => {
                const chosen = pick === k
                const isRight = Boolean(pick && k === 'A')
                return (
                  <button
                    key={k}
                    type="button"
                    role="radio"
                    aria-checked={chosen}
                    disabled={Boolean(pick)}
                    onClick={() => setPick(k)}
                    className={`flex min-h-14 items-center gap-4 rounded-card border px-5 text-left text-lg transition-all duration-300 ${
                      isRight
                        ? 'scale-[1.02] border-mint bg-mint text-ink'
                        : chosen
                          ? 'border-pink text-pink'
                          : 'hover:border-mint'
                    }`}
                  >
                    <span className="label-mono">{k}</span>
                    {v}
                    {isRight && <span className="label-mono ml-auto">{t('quiz_correct')}</span>}
                  </button>
                )
              })}
            </div>

            {pick && (
              <motion.div
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: Number.parseInt(motionTokens.reveal, 10) / 1000,
                  ease: motionTokens.revealEasing,
                }}
                className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t pt-5"
              >
                <p className="text-soft">{correct ? t('quiz_feedback_right') : t('quiz_feedback_wrong')}</p>
                <button
                  type="button"
                  onClick={() => setPick(null)}
                  className="label-mono min-h-11 rounded-stage border px-4 hover:border-mint hover:text-mint"
                >
                  {t('quiz_retry')}
                </button>
              </motion.div>
            )}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
