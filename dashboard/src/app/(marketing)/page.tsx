import type { Metadata } from 'next'
import HeroSection from '@/components/landing/HeroSection'
import SubjectsSection from '@/components/landing/SubjectsSection'
import PipelineSection from '@/components/landing/PipelineSection'
import TrustSection from '@/components/landing/TrustSection'
import JourneySection from '@/components/landing/JourneySection'
import AudiencesSection from '@/components/landing/AudiencesSection'
import AmharicSection from '@/components/landing/AmharicSection'
import StreamSection from '@/components/landing/StreamSection'
import ClosingSection from '@/components/landing/ClosingSection'
import FaqSection from '@/components/landing/FaqSection'
import { LazyAskDemo, LazyQuizDemo, LazyStatsSection } from '@/components/landing/LazySections'

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

/**
 * FAQ copy for schema.org. English literals on purpose: FAQPage JSON-Ld is a
 * search-engine artifact, not user-facing copy — the visible FAQ renders from
 * `messages/*` via FaqSection.
 */
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

/**
 * The landing page: the ported twelve-section composition, plus the two
 * sections this repo keeps from the old page (Stats — live `/auth/public-stats`,
 * and FAQ) before the closing CTA. Section order:
 * hero → ask demo → subjects → pipeline → trust → journey → quiz → audiences
 * → amharic → stream → stats → faq → final CTA.
 */
export default function LandingPage() {
  return (
    <>
      <JsonLd />
      <HeroSection />
      <LazyAskDemo />
      <SubjectsSection />
      <PipelineSection />
      <TrustSection />
      <JourneySection />
      <LazyQuizDemo />
      <AudiencesSection />
      <AmharicSection />
      <StreamSection />
      <LazyStatsSection />
      <FaqSection />
      <ClosingSection />
    </>
  )
}
