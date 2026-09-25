---
name: EthioSci
description: The EthioSci marketing surface — a near-black editorial science world with condensed uppercase display type, mono technical kickers, and jelly-mint/ultraviolet hazard accents.
colors:
  mint: "#3cffd0"
  violet: "#5200ff"
  white: "#ffffff"
  ink: "#131313"
  slate: "#2d2d2d"
  soft: "#e9e9e9"
  meta: "#949494"
  line: "rgba(255,255,255,.14)"
  link: "#3860be"
  sun: "#ffe633"
  pink: "#ff74bf"
  flame: "#ff7716"
  volt: "#0c84fa"
typography:
  display:
    fontFamily: "var(--font-anton), Impact, 'Arial Black', var(--font-ethiopic), 'Noto Sans Ethiopic', sans-serif"
    fontWeight: 400
    fontSize: "clamp(48px, 7vw, 104px)"
    lineHeight: 0.9
    letterSpacing: "-0.01em"
  body:
    fontFamily: "var(--font-grotesk), var(--font-inter), system-ui, var(--font-ethiopic), 'Noto Sans Ethiopic', sans-serif"
    fontWeight: 400
    fontSize: "16px"
  label:
    fontFamily: "var(--font-spacemono), var(--font-jbmono), 'Courier New', monospace"
    fontWeight: 400
    fontSize: "11px"
    lineHeight: 1.2
    letterSpacing: "0.18em"
rounded:
  input: "2px"
  micro: "4px"
  card: "20px"
  feature: "24px"
  stage: "30px"
  cta: "40px"
  pill: "9999px"
spacing:
  gutter: "20px"
  gutter-md: "32px"
  section-y: "96px"
  gap: "16px"
  gap-lg: "48px"
components:
  button-primary:
    backgroundColor: "{colors.mint}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.stage}"
    padding: "0 28px"
    height: "48px"
  button-primary-hover:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.stage}"
    padding: "0 28px"
    height: "48px"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.cta}"
    padding: "0 28px"
    height: "48px"
  button-header-cta:
    backgroundColor: "{colors.mint}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.cta}"
    padding: "0 20px"
    height: "44px"
  button-on-mint:
    backgroundColor: "{colors.violet}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.stage}"
    padding: "0 28px"
    height: "48px"
  panel:
    backgroundColor: "{colors.slate}"
    rounded: "{rounded.feature}"
    padding: "32px"
---

# Design System: EthioSci (Marketing Surface)

## Overview

**Creative North Star: "The Night-Lab Console."**

The EthioSci marketing surface (the `(marketing)` route group — landing, privacy, terms) is a near-black lab
ground ruled by hairlines and read out in mono, with billboard-scale condensed headlines shouting the offer
and two hazard-tape accents — jelly mint (`#3cffd0`) and ultraviolet (`#5200ff`) — marking anything the
visitor can act on. It refuses the category default (stock classroom photo, three benefit cards, gradient CTA
band): the page performs its own thesis — a knowledge-engine diagram, a typed answer with a citation, a
working quiz — so the visual system is built from diagrams, rasters-into-blend-modes, and technical labels
rather than illustration and shadow.

Density is editorial and rhythmic: every section opens with a numbered mono kicker, a huge Anton headline
with exactly one mint line, and content on a 1280px twelve-column grid separated from its neighbours by a
single hairline rule. Depth is done entirely with color blocks — page ink, slate panels, a full-bleed violet
band, a full-bleed mint closing band — never with shadow or gradient. Motion is one authored scroll reveal
(800ms rise+fade, `MotionConfig reducedMotion="user"`) plus slow looping SVG decoration; everything else is
instant.

This world was ported from a generated design whose own `src/styles.css` declared `--font-display: "Anton"`,
`--font-sans: "Space Grotesk"`, `--font-mono: "Space Mono"` — the build follows it verbatim. Provenance: the
concept-seed roll was **deliberately skipped** because the direction was brief-pinned (the user's brief made
preserving the generated design the assignment; per `reference/new-work.md`, "a user- or brief-pinned direction
beats the roll, always" — recorded in `.impeccable/build/state.json`). Approved deviations from the generated
source, confirmed by the user, are part of this surface's identity: the kept app shell (TeacherBanner,
EN/AM LanguageSwitcher, auth-aware "Launch App" pill, multi-column footer) and two kept sections (Stats `11 /`,
FAQ `12 /`) inserted between Stream and Closing. The eight shipping rasters in `public/landing/` each carry
source-repo provenance.

**Key Characteristics:**
- Near-black canvas (`#131313`) with hairline `white/14%` rules as the only dividers
- Jelly mint (`#3cffd0`) + ultraviolet (`#5200ff`) as hazard-tape accents; saturated color-block tiles, never tint washes
- Anton uppercase display at line-height 0.9 (48–104px); Space Mono 11px/0.18em kickers and buttons; Space Grotesk body
- Numbered `NN / Label` section kickers (01–10 from the generated source, 11/12 for the kept Stats + FAQ)
- Radius ladder 2/4/20/24/30/40 — pills for actions, rounded features for containers
- Zero shadows, zero gradients; depth by color blocking and image blend modes
- One authored scroll reveal, everything else instant; reduced motion honored

## Colors

The palette is a dark editorial ground with two brand hazards and four subject accents — accents appear as
full-strength blocks, never as soft tints.

### Primary
- **Jelly Mint** (`#3cffd0`): the primary accent. Primary CTA fills, focus rings, the last line of major
  headlines, progress fills, diagram nodes, link hover, the selected language segment, and the full-bleed
  closing band. On mint, text is ink.
- **Ultraviolet** (`#5200ff`): the secondary accent. The quiz section's full-bleed band, the learner's chat
  bubble, the closing-band primary button, the final diagram node.

### Tertiary (subject + state accents)
- **Sun** (`#ffe633`): Mathematics subject tile (with ink text) and highlight blocks.
- **Flame** (`#ff7716`): Chemistry stream events in the learning-stream feed.
- **Volt** (`#0c84fa`): Physics subject tile (with white text) and physics stream events.
- **Pink** (`#ff74bf`): wrong-answer state and pink highlights; never used for success.
- **Link Blue** (`#3860be`): the one blue — link hover accent, sourced from the app's `accentHover`.

### Neutral
- **Ink** (`#131313`): the page ground; also the text color on mint/sun fills (the "inverted" pairing).
- **Slate** (`#2d2d2d`): raised surfaces — chat/feature panels, language-toggle track, footer rule.
- **White** (`#ffffff`): headlines and primary text; also a deliberate block fill (hover state of the primary
  button, hero copy).
- **Soft** (`#e9e9e9`): body copy and nav links on ink.
- **Meta** (`#949494`): mono kickers, captions, footer meta text — technical readout voice.
- **Line** (`rgba(255,255,255,.14)`): every hairline — section separators, panel borders, grid texture. The
  dashboard's `rgba(255,255,255,.24)` border token is NOT this surface's norm; marketing markup uses `.14`.

### Named Rules
**The Hazard-Tape Rule.** Mint and violet earn their keep as solid fills on action targets and full-bleed
bands, and as single accent lines in display headlines. Never dilute them into translucent washes, glows, or
gradient stops.
**The Hairline Rule.** Structure is drawn with 1px `rgba(255,255,255,.14)` rules — between sections, around
panels, under headers. If a divider would be thicker or colored, the answer is a color block instead.

## Typography

**Display Font:** Anton (weight 400, falling back to Impact / `'Arial Black'` / Ethiopic stacks — `var(--font-anton)`)
**Body Font:** Space Grotesk (falling back to Inter / system-ui / Ethiopic stacks — `var(--font-grotesk)`)
**Label/Mono Font:** Space Mono (falling back to JetBrains Mono / Courier New — `var(--font-spacemono)`)

**Character:** A billboard and a readout. Anton shouts the promise in compressed uppercase; Space Mono
whispers the machine's status in tracked-out 11px caps; Space Grotesk does the quiet explaining. Every stack
ends in `var(--font-ethiopic)` / `Noto Sans Ethiopic` because the three Latin faces carry no Ethiopic glyphs.

### Hierarchy
- **Display** (Anton 400, `clamp(48px, 7vw, 104px)`, line-height 0.9, letter-spacing -0.01em, uppercase):
  section headlines and the hero. Hero h1 steps 54px → 80px (`sm`) → 104px (`lg`); section h2 steps
  48px → 72/80/88px (`md`); closing headline 56px → 104px; subject-tile names 48–96px.
- **Headline** (Space Grotesk 600–700, 18–24px, line-height ~1.2): in-panel titles, footer column heads set
  in label mono instead, stat values.
- **Title** (Space Grotesk 500–600, 16–18px): card titles, quiz options, ledes (`text-lg` 18px).
- **Body** (Space Grotesk 400, 16px, line-height 1.5–1.6): paragraphs; footer meta at 14px (`text-sm`).
- **Label** (Space Mono 400, 11px, letter-spacing 0.18em, uppercase, line-height 1.2): section kickers, nav
  links, all buttons, diagram chips, status readouts. Buttons add weight 700.

### Named Rules
**The Numbered-Kicker Rule.** Every section opens with a mono kicker in the form `NN / Label` (`01 / Ask
EthioSci` … `10 / Learning stream`, then `11 / Live data` and `12 / Answers` for the two kept sections). The
number is a two-digit ordinal of the page composition, not a heading level; the same mono voice doubles as the
in-panel readout (`RAG / Active`, `Mode / learn`).
**The One-Face-Per-Job Rule.** Anton is uppercase display only — never body, never small UI. Space Mono is
labels and buttons only. Body sentences are always Space Grotesk. The dashboard's Impact/.verge-display face
is a different world and must not appear on marketing surfaces.

## Layout

A single spatial model down the whole page: a `max-w-[1280px]` centered container with 20px gutters (`px-5`,
32px from `md` up), twelve columns at `lg`, and a 96px vertical section rhythm (`py-24`) with a 1px
`line` top border on every section (16 `border-t` separators across the composition).

- **Section skeleton (in order):** kicker → Anton h2 (one mint line) → content → hairline. Hero breaks it:
  three mono kicker lines staggered 120ms, then the three-line h1.
- **Column splits observed:** hero 7/5, AskDemo 4/8, Closing 8/4, footer 3-up; Subjects is a 12-column mosaic
  (7+2-row / 5 / 5 / 12) with 16px gaps (`gap-4`) and 320px-min tiles.
- **Responsive:** `sm` 640 / `md` 768 / `lg` 1024 / `xl` 1280 (Tailwind defaults, as used). Type steps at those
  breakpoints; grids collapse to one column below `md`; nav links collapse into a hamburger panel below `md`.
- **Header:** sticky, `py-5` at rest compressing to `py-2` after 40px of scroll (300ms), full-width `border-b`,
  inner container identical to page content so the wordmark, links, and CTA align to the grid.
- **Density:** generous between sections, tight inside panels (16–32px padding: `p-5`/`p-6`/`p-8`).

## Elevation & Depth

This system has no shadows at all — depth is communicated by tonal and chromatic blocking: ink page ground →
slate panels (`#2d2d2d`) for raised content → full-bleed violet (quiz) and mint (closing) bands that flip the
page's polarity, plus overlap (absolutely-positioned hero diagram over its raster) and image blend modes
(`mix-blend-luminosity` at 40% opacity under tile type). The one exception to the "no glass" instinct is the
sticky header, which ships `bg-ink/95 + backdrop-blur-md` — a legibility device confined to that single chrome
element (the direction contract said no glassmorphism; the build wins, and this is the only place it appears).

Focus is the system's only "raised" moment: `outline: 2px solid #3cffd0` with 3px offset on every
`:focus-visible` inside the marketing surface.

### Named Rules
**The No-Shadow Rule.** No `box-shadow`, no gradients, no glows anywhere on this surface. If two things need
separating, use a hairline; if a section needs lifting, change its background color.

## Shapes

The form language is a rounded ladder on a square stage: 2px (language-toggle segment), 4px (hero diagram
chips), 20px (chat bubbles, quiz options), 24px (feature panels, subject tiles, hero image frame), 30px
(primary buttons), 40px (secondary buttons, header CTA pill), pill/full (status dots, progress bars, the
hamburger button). Only the full-bleed section bands are square-cornered, because they run edge to edge.

Borders are always 1px hairlines (`line`, or `white/40` for the secondary button's stronger outline); imagery
is always clipped by its rounded container (`overflow-hidden`) with a border, never floated unframed. Nothing
gets a bevel, an inner ring, or a cut corner.

### Named Rules
**The Round-Ladder Rule.** Actions are rounder than containers: every button is a 30px or 40px pill; every
container sits at 20–24px. Never put a container radius on a button or a pill radius on a panel.

## Components

### Buttons
- **Shape:** primary `rounded-stage` (30px), secondary and header CTA `rounded-cta` (40px); no square corners.
- **Primary:** mint fill, ink text, label-mono weight 700, `px-7` (28px) with `min-h-12` (48px); optional
  trailing `→`. Used for the hero CTA and role-first sign-up (`/sign-up?role=…`).
- **Primary hover:** fill flips to white (`hover:bg-white`) — a color swap, never a lift or shadow.
- **Secondary / ghost:** transparent, 1px `white/40` border, white label-mono; hover turns border and text
  mint. On the mint closing band the pair inverts: violet fill (hover to ink) + 2px ink border (hover to
  ink fill / mint text).
- **Header CTA:** mint, `rounded-cta`, `px-5`, `min-h-11` (44px), auth-aware target (`/v2/overview` when
  logged in, `/login` otherwise); hover to white.
- **Focus:** global mint 2px outline, 3px offset. Touch targets ≥44px (`min-h-11`/`min-h-12`).

### Chips
- **Hero diagram steps:** `rounded-input` (2px) ink chips, `px-2 py-1`, label-mono white, prefixed with a
  two-digit ordinal — one per pipeline stage, laid over the SVG.
- **Status readouts:** bare label-mono (`● Status / online`, `RAG / active`) pinned to the hero panel corners,
  mint or meta colored.

### Cards / Containers
- **Corner Style:** `rounded-feature` (24px) for panels/tiles/frames; `rounded-card` (20px) for inner items.
- **Background:** slate for neutral panels; saturated fills (mint / violet / volt / sun) for subject tiles;
  ink for the hero frame and chat stage.
- **Shadow Strategy:** none (see Elevation). Separation = 1px `line` border.
- **Internal Padding:** 20–32px (`p-5` / `p-6` / `p-8`).
- **Subject tiles:** full-strength tone with the image beneath the type at `opacity-40 mix-blend-luminosity`,
  rising to `opacity-70` over 500ms on hover; mono index `01 /` and formula sit top row, Anton name bottom.
- **Quiz stage:** ink panel on the violet band — progress bar (pill track `bg-slate`, mint fill,
  `transition-all duration-700`), options below.

### Inputs / Fields
There are no text inputs on this surface. Two controls stand in:
- **Language toggle (EN/AM):** track `rounded-input` (2px), slate fill, 1px `line` border, `p-0.5`; segments
  are mono `text-xs` with `px-2.5 py-1` — active segment mint fill + ink bold text, inactive meta text going
  white on hover; `role="group"` + `aria-pressed`.
- **Quiz option:** `rounded-card` (20px), 1px `line` border, `min-h-14` (56px), `px-5`, 18px text, left
  aligned. States: default (white text) → hover border mint → correct `scale-[1.02]` mint fill + ink text →
  wrong border/text pink. Transitions 300ms.

### Navigation
- **Header:** sticky, `bg-ink/95 backdrop-blur-md`, hairline bottom border, compresses `py-5 → py-2` past
  40px scroll. Wordmark is Anton `text-2xl` with a mint `Sci`; links are label-mono soft → mint on hover;
  hamburger (`rounded-full`, hairline) below `md` opens an inline panel of full-width `min-h-12` mono rows.
- **TeacherBanner (kept app chrome):** thin ink bar above the header, hairline `border-slate`, 14px soft copy
  with a mint bold link; dismissible to `localStorage`, hidden by default when already dismissed.
- **Footer (kept app chrome):** 3-column grid on ink, `border-t border-slate`, label-mono white headings,
  Space Mono `text-sm` links hovering mint, meta copyright row under a hairline.

### Signature Components
- **`Reveal` (scroll reveal):** framer-motion `whileInView`, once — `opacity 0→1`, `y 24→0`, `scale .98→1`,
  800ms on bezier `[0.2, 0.7, 0.2, 1]`, `viewport amount 0.15`; stagger via `delay = index * 100` ms. Wrapped
  once in `MotionConfig reducedMotion="user"`, and CSS `anim-*` loops are disabled under
  `prefers-reduced-motion`. Entrances elsewhere (hero rise) use the same 800ms/`rise(40px)` token pair.
- **`Label` (kicker):** renders `.label-mono`, defaulting to `text-meta` unless the caller passes its own
  `text-*` class.
- **Hero stage:** square `rounded-feature` frame — raster (`hero-dna.jpg`) at 45% opacity under an SVG engine:
  dashed ring (`anim-spin`, 40s), six zig-zag mint connectors (`anim-draw`, 1.4s, staggered 220ms from
  1200ms), stacked `NN + stage` chips, status readouts; the AskDemo answer types out behind a mint `caret`
  (1s blink) and reveals its CTA row on completion.
- **Sci-grid:** the hero's measuring texture — two 1px `white/14%` gradients at `64px 64px`, at 40% opacity,
  `aria-hidden`. It is the generated design's own hero texture (the craft-floor `codex-grid-background`
  advisory is recorded as a reasoned ignore in `.impeccable/config.json`, not as a rule).

## Do's and Don'ts

### Do:
- **Do** open every section with the numbered mono kicker `NN / Label` and an Anton h2 that carries exactly
  one mint line.
- **Do** separate sections and panels with 1px `rgba(255,255,255,.14)` rules on the `#131313` ground.
- **Do** use the marketing token vocabulary only — `ink / slate / mint / violet / meta / soft / line / link /
  sun / pink / flame / volt` and radii `input / micro / card / feature / stage / cta` (the names exported
  from `design-system.ts` are the only color/radius vocabulary allowed in marketing markup).
- **Do** ship bilingual parity: every `landing.*` key exists in both `messages/en.json` and `messages/am.json`
  (175 keys each, strict parity), and EN/AM ship together in the same change. Mono notation (`09 / Lang /
  EN + AM`, `RAG / Active`) stays literal in both locales.
- **Do** honor the floor of the accessibility brief: 44px minimum targets, mint focus-visible outline,
  `prefers-reduced-motion` (CSS `anim-*` disabled; framer reveals follow `reducedMotion="user"`), semantic
  heading order, and Ethiopic fallback in every font stack.
- **Do** treat imagery as material: generated rasters sit under type at 40–45% opacity with
  `mix-blend-luminosity`, always clipped by a rounded, bordered container, lazy-loaded below the fold.
- **Do** route CTAs to role-first sign-up (`/sign-up?role=learner|teacher|parent`) and let the header pill be
  auth-aware.

### Don't:
- **Don't** add shadows, gradients, glows, or glass panels anywhere — including on cards and buttons. The
  sticky header's `backdrop-blur-md` is the single sanctioned exception.
- **Don't** put Anton on body copy or labels, or Space Mono on sentences (One-Face-Per-Job).
- **Don't** dilute mint/violet into translucent washes or use them as body-text colors (Hazard-Tape Rule);
  keep accents under roughly a tenth of any viewport except the two sanctioned full-bleed bands.
- **Don't** invent proof: no fabricated stats, testimonials, logos, pricing, or awards. Platform numbers come
  from the real `GET /auth/public-stats` endpoint only — `StatsSection` renders a skeleton while loading and
  an em dash plus `stats_error` on failure (the fabricated fallback numbers were removed; the live badge
  appears only when counts are actually in). This surface's cleanup is the pattern to repeat.
- **Don't** hardcode copy in components — all visible strings come from `messages/*` under the `landing.`
  namespace; JSON-Ld/SEO literals are the documented exception.
- **Don't** reuse dashboard-world faces or token names on this surface (Impact/.verge-display, `v2-*`,
  `primary`, `border` at white/.24) — they belong to the app shell outside `.mk-surface`.
