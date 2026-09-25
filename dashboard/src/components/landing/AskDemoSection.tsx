'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { useInView } from '@/hooks/useInView'
import { Label } from './Reveal'

/**
 * "01 / Ask EthioSci" — the chat demo. The answer types itself once the panel
 * scrolls into view; with `prefers-reduced-motion` it renders complete. The
 * citation chips fade in after typing finishes. Mocked client-side only (no
 * API call, per the design brief).
 */
export default function AskDemoSection() {
  const t = useTranslations('landing')
  const { ref, inView } = useInView<HTMLDivElement>(0.3)
  const answer = t('ask_answer')
  const [n, setN] = useState(0)

  useEffect(() => {
    if (!inView) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setN(answer.length)
      return
    }
    const id = setInterval(() => {
      setN((v) => {
        if (v >= answer.length) {
          clearInterval(id)
          return v
        }
        return v + 3
      })
    }, 18)
    return () => clearInterval(id)
  }, [inView, answer])

  const done = n >= answer.length

  return (
    <section id="learn" className="border-t">
      <div className="mx-auto grid max-w-[1280px] gap-12 px-5 py-24 md:px-8 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <Label>{t('ask_kicker')}</Label>
          <h2 className="display mt-6 text-[48px] md:text-[72px]">{t('ask_title')}</h2>
          <p className="mt-6 max-w-sm text-soft">{t('ask_desc')}</p>
        </div>

        <div ref={ref} className="rounded-feature border bg-slate p-5 md:p-8 lg:col-span-8">
          <div className="flex items-center justify-between border-b pb-4">
            <Label>Mode / learn</Label>
            <p className="label-mono text-mint">RAG / Verified / Curriculum grounded</p>
          </div>

          <div className="mt-6 flex justify-end">
            <p className="max-w-md rounded-card bg-violet px-5 py-4 text-white">
              {t('ask_question')}
            </p>
          </div>

          <div className="mt-6 max-w-2xl">
            <Label className="text-mint">EthioSci</Label>
            <p className={`mt-3 min-h-[9rem] text-lg leading-relaxed ${done ? '' : 'caret'}`}>
              {answer.slice(0, n)}
            </p>
            <div
              className={`mt-6 flex flex-wrap gap-3 transition-opacity duration-700 ${
                done ? 'opacity-100' : 'opacity-0'
              }`}
            >
              <span className="label-mono rounded-input bg-mint px-3 py-2 font-bold text-ink">
                {t('ask_cite_1')}
              </span>
              <span className="label-mono rounded-input border border-mint/50 px-3 py-2 text-mint">
                {t('ask_cite_2')}
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
