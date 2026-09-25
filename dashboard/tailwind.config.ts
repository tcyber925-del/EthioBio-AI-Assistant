import type { Config } from 'tailwindcss';
import { marketing, marketingTypography, radii } from './src/styles/design-system';

/**
 * Tailwind config.
 *
 * Converted from `tailwind.config.js` so the theme can import
 * `src/styles/design-system.ts` — the documented single source of truth for
 * tokens. Existing dashboard tokens (`v2-*`, `primary`, `accent`, font stacks)
 * are unchanged; the `ink`/`mint`/... block below is the `(marketing)` world.
 */
const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        background: 'var(--v2-bg)',
        'background-secondary': 'var(--v2-surface)',
        foreground: 'var(--v2-text-primary)',
        'foreground-muted': 'var(--v2-text-secondary)',
        border: 'var(--v2-border)',
        'border-light': 'var(--v2-border-strong)',
        card: 'var(--v2-surface)',
        'card-hover': 'color-mix(in srgb, var(--v2-surface) 97%, var(--v2-text-primary) 3%)',
        primary: {
          DEFAULT: '#10b981',
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
          hover: '#059669',
        },
        accent: {
          gold: '#f59e0b',
          teal: '#2dd4bf',
          earth: '#a16207',
        },
        /* DashboardV2 design tokens — alpha-compatible via color-mix */
        'v2-bg': 'color-mix(in srgb, var(--v2-bg) calc(100% * <alpha-value>), transparent)',
        'v2-surface': 'color-mix(in srgb, var(--v2-surface) calc(100% * <alpha-value>), transparent)',
        'v2-text-primary': 'color-mix(in srgb, var(--v2-text-primary) calc(100% * <alpha-value>), transparent)',
        'v2-text-secondary': 'color-mix(in srgb, var(--v2-text-secondary) calc(100% * <alpha-value>), transparent)',
        'v2-border': 'var(--v2-border)',
        'v2-accent': 'color-mix(in srgb, var(--v2-accent) calc(100% * <alpha-value>), transparent)',
        'v2-accent-hover': 'color-mix(in srgb, var(--v2-accent-hover) calc(100% * <alpha-value>), transparent)',
        'v2-accent-muted': 'var(--v2-accent-muted)',
        'v2-success': 'color-mix(in srgb, var(--v2-success) calc(100% * <alpha-value>), transparent)',
        'v2-warning': 'color-mix(in srgb, var(--v2-warning) calc(100% * <alpha-value>), transparent)',
        'v2-error': 'color-mix(in srgb, var(--v2-error) calc(100% * <alpha-value>), transparent)',
        'v2-purple-rule': 'color-mix(in srgb, var(--v2-purple-rule) calc(100% * <alpha-value>), transparent)',
        'v2-link-hover': 'color-mix(in srgb, var(--v2-link-hover) calc(100% * <alpha-value>), transparent)',
        'v2-inverted': 'color-mix(in srgb, var(--v2-inverted) calc(100% * <alpha-value>), transparent)',
        /* Marketing surface (design-system.ts → `marketing`) */
        ink: marketing.ink,
        slate: marketing.slate,
        mint: marketing.mint,
        violet: marketing.violet,
        meta: marketing.meta,
        soft: marketing.soft,
        line: marketing.line,
        link: marketing.link,
        sun: marketing.sun,
        pink: marketing.pink,
        flame: marketing.flame,
        volt: marketing.volt,
      },
      borderRadius: {
        /* design-system.ts radii — marketing scale (2/4/20/24/30/40) */
        input: radii.input,
        micro: radii.micro,
        card: radii.card,
        feature: radii.feature,
        stage: radii.stage,
        cta: radii.cta,
      },
      fontFamily: {
        sans: [
          'var(--font-inter)',
          'system-ui',
          'var(--font-ethiopic)',
          'Noto Sans Ethiopic',
          'sans-serif',
        ],
        display: [
          'var(--font-spectral)',
          'Georgia',
          'var(--font-ethiopic)',
          'Noto Sans Ethiopic',
          'serif',
        ],
        mono: ['var(--font-jbmono)', 'monospace'],
        /* Marketing surface stacks (design-system.ts → `marketingTypography`) */
        grotesk: [
          marketingTypography.body,
        ],
        ethiopic: ['var(--font-ethiopic)', 'Noto Sans Ethiopic', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
