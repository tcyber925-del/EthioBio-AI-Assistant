---
version: 1
slug: "dashboard-src-app-marketing-page-tsx"
primary_target: "dashboard/src/app/(marketing)/page.tsx"
related_targets: ["dashboard/src/components/landing","dashboard/src/styles/design-system.ts"]
---

# Surface brief — `(marketing)` landing page

## Scope and visitor mode

Mode: **Persuade**. Route `/` (and the `(marketing)` group chrome). Visitor: an
Ethiopian learner, teacher or parent deciding in seconds whether this is real; the
page must make the offer intelligible, show a visible primary action, and demonstrate
the citation mechanism. Success = role-first sign-up. Failure mode confirmed by the
user: **drift from the generated design**.

## Direction contract

**THESIS:** EthioSci proves curriculum grounding by performing it — a knowledge-engine
diagram, a typed answer with a real citation, a working quiz — instead of claiming it.
It refuses the category default: stock classroom photo, three benefit cards, gradient
CTA band.

**OWN-WORLD:** near-black `#131313` canvas; jelly-mint `#3cffd0` and ultraviolet
`#5200ff` on white/grey neutrals; Anton condensed uppercase display, Space Grotesk
body, Space Mono technical labels; hairline `white/14%` rules, radius scale
2/4/20/24/30/40; no shadows, no gradients, no glassmorphism.

**STORY:** the visitor learns this is an Ethiopian science tutor that cites grade, unit
and page; sees it answer and verify; tries a quiz question; picks their role; signs up
free (teachers via the persistent banner).

**FIRST VIEWPORT:** sticky mono nav (ETHIOSCI wordmark · LEARN / SUBJECTS / HOW IT
WORKS / FOR TEACHERS · START LEARNING pill) above a split hero — left column: three
mono kicker lines, a 54–104px three-line `SCIENCE, BUILT FOR ETHIOPIA.` with the last
line mint, one body paragraph, mint primary CTA + outlined secondary CTA; right column:
square bordered panel with the animated QUESTION→UNDERSTAND→RETRIEVE→VERIFY→EXPLAIN→
MASTER SVG diagram over a low-contrast DNA image; faint sci-grid across the section.

**FORM:** the generated design's twelve-section composition (Nav, Hero, AskDemo,
Subjects, Pipeline, Trust, Journey, QuizDemo, Audiences, Amharic, Stream, Final CTA),
**brief-pinned — position: the only candidate.** The user- and brief-pinned direction
beats the roll, so `concept-seed` was deliberately not run and printed no seed key;
the generated page is the assigned direction, ported into this repo's architecture.

**FINISH:** unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.

## Unresolved decisions

- Amharic strings: my translations ship with EN in the same PR, flagged for
  native-speaker review (project-wide open item).
- `StatsSection` fallback numbers: replace fabricated defaults with loading/honest
  states (user-approved recommendation).
