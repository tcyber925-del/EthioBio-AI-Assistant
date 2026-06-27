/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        'background-secondary': 'var(--background-secondary)',
        foreground: 'var(--foreground)',
        'foreground-muted': 'var(--foreground-muted)',
        border: 'var(--border)',
        'border-light': 'var(--border-light)',
        card: 'var(--card)',
        'card-hover': 'var(--card-hover)',
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
      },
      fontFamily: {
        display: ['Spectral', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
