export const colors = {
  background: '#131313',
  surface: '#2d2d2d',
  textPrimary: '#ffffff',
  textSecondary: '#949494',
  border: 'rgba(255,255,255,.24)',
  borderStrong: '#ffffff',
  accent: '#3cffd0',
  accentHover: '#3860be',
  accentMuted: 'rgba(60, 255, 208, 0.12)',
  purple: '#5200ff',
  purpleRule: '#3d00bf',
  mintBorder: '#309875',
  focus: '#1eaedb',
  inverted: '#000000',
  imageFrame: '#313131',
  success: '#3cffd0',
  warning: '#ffcc00',
  error: '#ff4fa3',
  neutral: {
    50: '#ffffff',
    100: '#e9e9e9',
    200: '#c2c2c2',
    300: '#949494',
    400: '#8c8c8c',
    500: '#666666',
    600: '#444444',
    700: '#313131',
    800: '#2d2d2d',
    900: '#131313',
  },
} as const;

export const typography = {
  display: {
    fontFamily: "Impact, 'Arial Black', 'Helvetica Neue Condensed', Helvetica, sans-serif",
    fontWeight: 900,
    lineHeight: 0.95,
    letterSpacing: '0.8px',
    textTransform: 'uppercase',
  },
  heading: {
    fontSize: '24px',
    fontWeight: 700,
    lineHeight: 1,
  },
  subheading: {
    fontSize: '18px',
    fontWeight: 600,
    lineHeight: 1.2,
    letterSpacing: '1.2px',
    textTransform: 'uppercase',
  },
  body: {
    fontSize: '14px',
    fontWeight: 400,
    lineHeight: 1.5,
  },
  caption: {
    fontFamily: "'JetBrains Mono', 'Space Mono', 'Courier New', monospace",
    fontSize: '11px',
    fontWeight: 600,
    lineHeight: 1.2,
    letterSpacing: '1.4px',
    textTransform: 'uppercase',
  },
} as const;

export const spacing = {
  section: '32px',
  cardPadding: '24px',
  pagePaddingX: '40px',
  pagePaddingY: '32px',
  sidebarExpanded: '256px',
  sidebarCollapsed: '72px',
} as const;

export const shadows = {
  card: 'inset 0 0 0 1px rgba(255,255,255,.24)',
  elevated: 'inset 0 0 0 1px #3cffd0',
  sidebar: '1px 0 0 rgba(255,255,255,.24)',
} as const;

export const radii = {
  card: '20px',
  feature: '24px',
  button: '24px',
  pill: '9999px',
  input: '2px',
  micro: '4px',
  stage: '30px',
  cta: '40px',
} as const;

export const motion = {
  pageTransition: '180ms',
  sidebar: '180ms',
  cardReveal: '150ms',
  activityUpdate: '150ms',
  easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
  /** Scroll-reveal entrance (marketing `Reveal`): rise + fade, once. */
  reveal: '800ms',
  /** Bezier [x1, y1, x2, y2] — the framer-motion form of cubic-bezier(0.2, 0.7, 0.2, 1). */
  revealEasing: [0.2, 0.7, 0.2, 1] as [number, number, number, number],
} as const;

/**
 * Marketing surface (the `(marketing)` route group: landing, privacy, terms).
 * The dark editorial world: near-black canvas, jelly-mint + ultraviolet,
 * Anton display / Space Grotesk body / Space Mono labels.
 *
 * Tailwind (`tailwind.config.ts`) imports this directly — these names are the
 * only color/radius vocabulary allowed in marketing markup. Hex values for
 * `ink`/`slate`/`mint`/`violet`/`meta`/`soft`/`link` match the canonical
 * `colors` above; the four accents carry no hex in their source, so they are
 * converted from their origin oklch coordinates.
 */
export const marketing = {
  /** Canvas / near-black page ground. */
  ink: colors.background,
  /** Raised surface: panels, tiles, figcaptions. */
  slate: colors.surface,
  /** Primary accent: jelly mint. */
  mint: colors.accent,
  /** Secondary accent: ultraviolet. */
  violet: colors.purple,
  /** Technical/meta text on ink. */
  meta: colors.textSecondary,
  /** Body text on ink. */
  soft: colors.neutral[100],
  /** Hairline rules and default border color (white at 14%). */
  line: 'rgba(255,255,255,.14)',
  /** Link / hover accent. */
  link: colors.accentHover,
  /** Subject accent — Mathematics tile, highlights. */
  sun: '#ffe633',
  /** Subject accent — wrong-answer state, highlights. */
  pink: '#ff74bf',
  /** Subject accent — Chemistry stream events. */
  flame: '#ff7716',
  /** Subject accent — Physics tile and stream events. */
  volt: '#0c84fa',
} as const;

/**
 * Marketing type stacks. Loaded in `src/app/layout.tsx` via next/font; every
 * stack ends in the Ethiopic fallbacks because Anton/Space Grotesk/Space Mono
 * carry no Ethiopic glyphs.
 */
export const marketingTypography = {
  /** Condensed uppercase display face (`.display`). */
  display:
    'var(--font-anton), Impact, \'Arial Black\', var(--font-ethiopic), \'Noto Sans Ethiopic\', sans-serif',
  /** Body face (applied on the marketing surface root). */
  body:
    'var(--font-grotesk), var(--font-inter), system-ui, var(--font-ethiopic), \'Noto Sans Ethiopic\', sans-serif',
  /** Technical labels (`.label-mono`). */
  label:
    'var(--font-spacemono), var(--font-jbmono), \'Courier New\', monospace',
} as const;
