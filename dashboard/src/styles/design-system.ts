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
    fontSize: '60px',
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
} as const;

export const motion = {
  pageTransition: '180ms',
  sidebar: '180ms',
  cardReveal: '150ms',
  activityUpdate: '150ms',
  easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
} as const;
