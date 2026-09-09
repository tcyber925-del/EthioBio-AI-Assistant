'use client'

import { useTranslations } from 'next-intl'
import { motion, MotionConfig } from 'framer-motion'
import Link from 'next/link'
import { MessageSquare } from 'lucide-react'

export default function HeroSection() {
  const t = useTranslations('landing')

  return (
    <MotionConfig reducedMotion="user">
      <section className="relative overflow-hidden border-b border-[#2d2d2d] bg-gradient-to-b from-[#181818] to-[#131313] pb-24 pt-20">
        <div className="relative z-10 mx-auto max-w-7xl px-4 text-center sm:px-6 lg:px-8">
          <motion.span
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="verge-label mb-6 inline-block rounded-sm border border-[#3cffd0]/30 bg-[#3cffd0]/10 px-3 py-1 text-[#3cffd0]"
          >
            {t('hero_kicker')}
          </motion.span>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="verge-display mx-auto mb-6 max-w-5xl text-4xl font-extrabold leading-none tracking-tighter text-white sm:text-6xl md:text-7xl"
          >
            {t('hero_title')}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="mx-auto mb-10 max-w-3xl text-lg leading-relaxed text-gray-400 font-sans sm:text-xl"
          >
            {t('hero_subtitle')}
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="flex flex-col items-center justify-center gap-4 sm:flex-row"
          >
            <Link
              href="/sign-up?role=learner"
              className="w-full rounded-none border border-black bg-[#3cffd0] px-8 py-4 text-center font-mono text-sm font-bold uppercase tracking-wider text-black transition-all hover:-translate-x-[3px] hover:-translate-y-[3px] hover:bg-[#2be0b5] hover:shadow-[4px_4px_0px_0px_#5200ff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0] focus-visible:ring-offset-2 focus-visible:ring-offset-[#131313] sm:w-auto"
            >
              {t('hero_cta_start')}
            </Link>
            <a
              href="https://t.me/ethiobio_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="flex w-full items-center justify-center space-x-2 rounded-none border border-gray-600 bg-transparent px-8 py-4 text-center font-mono text-sm font-bold uppercase tracking-wider text-white transition-all hover:border-white hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0] sm:w-auto"
            >
              <MessageSquare className="h-4 w-4 text-[#3cffd0]" />
              <span>{t('cta_telegram')}</span>
            </a>
          </motion.div>

          <p className="mt-6 text-sm text-gray-400">
            <Link
              href="/login"
              className="underline decoration-gray-600 underline-offset-4 transition-colors hover:text-white hover:decoration-[#3cffd0] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0]"
            >
              {t('cta_login')}
            </Link>
          </p>
        </div>

        {/* Decorative Grid Lines */}
        <div className="pointer-events-none absolute inset-0 z-0 bg-[linear-gradient(to_right,#1b1b1b_1px,transparent_1px),linear-gradient(to_bottom,#1b1b1b_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)]" />
      </section>
    </MotionConfig>
  )
}