import type { Metadata } from 'next'
import { getTranslations } from 'next-intl/server'
import {
  Award,
  BookOpen,
  Brain,
  GraduationCap,
  MessageSquare,
  Users,
  Zap,
} from 'lucide-react'
import Link from 'next/link'
import HeroSection from '@/components/landing/HeroSection'
import FaqSection from '@/components/landing/FaqSection'
import { LazyConsoleTabs, LazyStatsSection } from '@/components/landing/LazySections'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://ethiosci.app'

export const metadata: Metadata = {
  title: 'EthioSci — Science Learning for Ethiopian Grades 7–12',
  description:
    'Personalized science tutoring in biology, chemistry, physics and mathematics for Ethiopian Grades 7–12, grounded in the national curriculum textbooks.',
  alternates: { canonical: '/' },
  openGraph: {
    title: 'EthioSci — Science Learning for Ethiopian Grades 7–12',
    description:
      'Personalized science tutoring in biology, chemistry, physics and mathematics for Ethiopian Grades 7–12, grounded in the national curriculum textbooks.',
    type: 'website',
    url: SITE_URL,
    siteName: 'EthioSci',
    locale: 'en_US',
  },
}

const FAQ = [
  {
    q: 'Is EthioSci free?',
    a: 'Yes — free for learners. EthioSci is sustained by grants and supporters.',
  },
  {
    q: 'Which subjects and grades?',
    a: 'Biology, chemistry, physics and mathematics for Grades 7–12, aligned to the Ethiopian curriculum.',
  },
  {
    q: 'Do you support Amharic?',
    a: 'Yes — the app and the answers work in both Amharic and English.',
  },
  {
    q: 'How does EthioSci work on Telegram?',
    a: 'Search @ethiobio_bot — ask questions and take quizzes with low data usage.',
  },
  {
    q: 'Where do answers come from?',
    a: 'Ethiopian textbooks with citations — every answer is grounded in the curriculum.',
  },
  {
    q: 'What do teachers get?',
    a: 'A lesson-plan copilot, practice assignments and progress tracking.',
  },
  {
    q: 'How does adaptive quizzing work?',
    a: "Difficulty adapts to each student's answers, with an explanation after every question.",
  },
  {
    q: 'How is student data handled?',
    a: 'Minimal data, no ads. Your date of birth is used only for an age-appropriate experience.',
  },
]

function JsonLd() {
  const organization = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'EthioSci',
    url: SITE_URL,
    sameAs: ['https://t.me/ethiobio_bot'],
  }
  const faqPage = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQ.map((item) => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  }
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organization) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqPage) }}
      />
    </>
  )
}

export default async function LandingPage() {
  const t = await getTranslations('landing')

  const rolePanels: Array<{
    role: string
    kicker: string
    titleKey: string
    descKey: string
    icon: typeof Award
  }> = [
    { role: 'learner', kicker: 'Core Track', titleKey: 'role_student_title', descKey: 'role_student_desc', icon: MessageSquare },
    { role: 'teacher', kicker: 'Educator Workspace', titleKey: 'role_teacher_title', descKey: 'role_teacher_desc', icon: Users },
    { role: 'parent', kicker: 'Family Circle', titleKey: 'role_parent_title', descKey: 'role_parent_desc', icon: Award },
  ]

  const features: Array<{ icon: typeof BookOpen; titleKey: string; descKey: string; tag: string }> = [
    { icon: BookOpen, titleKey: 'feature_textbook', descKey: 'feature_textbook_desc', tag: 'Citations verified' },
    { icon: Brain, titleKey: 'feature_gamification', descKey: 'feature_gamification_desc', tag: 'Bayesian IRT estimation' },
    { icon: Zap, titleKey: 'feature_recovery', descKey: 'feature_recovery_desc', tag: 'Automatic recovery' },
    { icon: GraduationCap, titleKey: 'feat_copilot_title', descKey: 'feat_copilot_desc', tag: 'Aligned to Grades 7-12' },
  ]

  return (
    <div className="min-h-screen bg-[#131313]">
      <JsonLd />
      <HeroSection />
      <LazyConsoleTabs />
      <section id="features" className="border-b border-[#2d2d2d] bg-[#181818] py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-16 text-center">
            <h2 className="verge-display mb-4 text-3xl text-white sm:text-4xl">{t('section_features')}</h2>
            <p className="mx-auto max-w-xl font-sans text-gray-400">{t('features_subtitle')}</p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, titleKey, descKey, tag }) => (
              <div
                key={titleKey}
                className="flex flex-col justify-between border border-[#2d2d2d] bg-[#131313] p-6 transition-colors hover:border-[#3cffd0]"
              >
                <div>
                  <Icon className="mb-4 h-8 w-8 text-[#3cffd0]" />
                  <h3 className="verge-label text-base text-white">{t(titleKey)}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-gray-400">{t(descKey)}</p>
                </div>
                <span className="mt-6 font-mono text-[10px] text-gray-600">{tag}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-[#2d2d2d] py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
            {rolePanels.map(({ role, kicker, titleKey, descKey, icon: Icon }) => (
              <Link
                key={role}
                href={`/sign-up?role=${role}`}
                className="group relative block overflow-hidden border border-[#2d2d2d] bg-[#181818] p-8 transition-all hover:border-[#5200ff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3cffd0] focus-visible:ring-offset-2 focus-visible:ring-offset-[#131313]"
              >
                <span className="verge-label mb-4 block text-[#3cffd0]">{kicker}</span>
                <h3 className="verge-display mb-4 text-2xl font-black text-white">{t(titleKey)}</h3>
                <p className="mb-6 font-sans text-sm leading-relaxed text-gray-400">{t(descKey)}</p>
                <span className="text-sm font-medium text-[#3cffd0] opacity-0 transition-opacity group-hover:opacity-100">
                  {t('banner_signup_free')} →
                </span>
                <div className="absolute bottom-0 right-0 translate-x-4 translate-y-4 p-4 opacity-10 transition-transform group-hover:translate-x-0 group-hover:translate-y-0 group-hover:opacity-40">
                  <Icon className="h-16 w-16 text-[#3cffd0]" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <FaqSection />
      <LazyStatsSection />
    </div>
  )
}