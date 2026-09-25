# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: Ethiopian learners in Grades 7–12 studying biology, chemistry, physics and
mathematics, working in English or Amharic, often on low-bandwidth devices.

Secondary audiences (confirmed, secondary only): teachers (lesson-plan copilot,
assignments, progress tracking) and parents (visibility into a child's progress).

## Product Purpose

EthioSci is a multi-subject science learning and teaching assistant. It answers
science questions, runs adaptive quizzes, and turns answers into practice until a
learner masters a topic. Success means a learner gets a correct, curriculum-grounded
answer and returns to practice; the product is sustained by grants, so it stays free
for learners.

## Positioning

Answers are grounded in the Ethiopian national curriculum textbooks and cited to
grade, unit and page — the citation is the mechanism a neighbouring product could not
truthfully copy. A Telegram bot (@ethiobio_bot) delivers the same capability with low
data usage.

## Operating Context

- Web app (Next.js) + FastAPI backend + Telegram bot; deployment on Vercel (dashboard),
  Render (API/bot), with the marketing surface at `/`.
- Learners arrive on mobile as often as desktop; bilingual EN/AM is a product
  requirement, not a nicety.
- The Telegram channel is a real, shipped workflow (ask questions, take quizzes).

## Capabilities and Constraints

- Subjects: biology, chemistry, physics, mathematics; Grades 7–12.
- Landing page CTAs route to role-first sign-up (`/sign-up?role=learner|teacher|parent`)
  and login; the header CTA routes logged-in users to the app.
- Platform counts come from the real `GET /auth/public-stats` endpoint. If it fails,
  numbers must not be invented or fabricated as fallbacks.
- Undecided product facts are recorded, not invented (see Evidence on Hand).

## Brand Commitments

- Product name: **EthioSci**. Generic subject term: "science" (science Q&A, science
  tutor). Subjects always listed as biology, chemistry, physics, mathematics.
- Historical infrastructure identifiers stay `ethiobio_*` (services, datasets, bot
  handle, localStorage keys) — do not rename them.
- Telegram: `https://t.me/ethiobio_bot` is the canonical bot link.
- Voice: direct, editorial, no hype; the user confirmed the generated landing design
  is the binding visual brief for the marketing surface ("drift from the generated
  design" is the stated failure mode).

## Evidence on Hand

- Live platform counts via `GET /auth/public-stats` (dashboard `StatsSection`).
- Curriculum textbook corpus (`data/textbooks/`) and citation format
  `(Grade X, Unit Y: Title, p. Z)`.
- Eight generated editorial images staged for the landing page
  (source repo `src/assets/*.jpg`, to be copied to `dashboard/public/landing/`).
- Existing FAQ content (8 Q&As) with EN + AM translations.

Explicit absences — future work must not fabricate them: no testimonials, no customer
or school logos, no pricing, no awards/press. The design brief also forbids invented
statistics (no fake student counts, accuracy figures, or benchmarks).

## Product Principles

1. Ground every claim in the curriculum or in a real endpoint; never invent proof.
2. Free for learners stays true — no pricing or paywall surfaces.
3. Bilingual by default: every surface ships EN and AM together.
4. Low bandwidth is a first-class constraint: light pages, lazy-loaded media.
5. Preserve the product's real mechanisms (citations, adaptive quiz, Telegram) in any
   surface rather than describing them abstractly.

## Accessibility & Inclusion

- Full EN/AM parity on marketing copy; Amharic rendering requires Ethiopic font
  fallbacks in every display/mono stack (Anton, Space Grotesk, Space Mono carry no
  Ethiopic glyphs).
- WCAG-level basics on the marketing surface: keyboard-reachable controls, visible
  focus, `prefers-reduced-motion` honored, 44px touch targets, semantic headings.
