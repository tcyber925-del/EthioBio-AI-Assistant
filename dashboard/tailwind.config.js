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
        },
        accent: {
          gold: '#f59e0b',
          teal: '#2dd4bf',
          earth: '#a16207',
        },
        /* DashboardV2 design tokens */
        'v2-bg': 'var(--v2-bg)',
        'v2-surface': 'var(--v2-surface)',
        'v2-text-primary': 'var(--v2-text-primary)',
        'v2-text-secondary': 'var(--v2-text-secondary)',
        'v2-border': 'var(--v2-border)',
        'v2-accent': 'var(--v2-accent)',
        'v2-accent-hover': 'var(--v2-accent-hover)',
        'v2-accent-muted': 'var(--v2-accent-muted)',
        'v2-success': 'var(--v2-success)',
        'v2-warning': 'var(--v2-warning)',
        'v2-error': 'var(--v2-error)',
      },
      fontFamily: {
        display: ['Spectral', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
