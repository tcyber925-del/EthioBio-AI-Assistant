export const colors = {
  background: '#FAFAFA',
  surface: '#FFFFFF',
  textPrimary: '#0F172A',
  textSecondary: '#64748B',
  border: '#E5E7EB',
  accent: '#14B8A6',
  accentHover: '#0D9488',
  accentMuted: 'rgba(20, 184, 166, 0.1)',
  success: '#22C55E',
  warning: '#F59E0B',
  error: '#EF4444',
  neutral: {
    50: '#FAFAFA',
    100: '#F5F5F5',
    200: '#E5E5E5',
    300: '#D4D4D4',
    400: '#A3A3A3',
    500: '#737373',
    600: '#525252',
    700: '#404040',
    800: '#262626',
    900: '#171717',
  },
} as const;

export const typography = {
  display: {
    fontSize: '36px',
    fontWeight: 700,
    lineHeight: 1.1,
  },
  heading: {
    fontSize: '24px',
    fontWeight: 600,
    lineHeight: 1.3,
  },
  subheading: {
    fontSize: '18px',
    fontWeight: 600,
    lineHeight: 1.4,
  },
  body: {
    fontSize: '14px',
    fontWeight: 400,
    lineHeight: 1.5,
  },
  caption: {
    fontSize: '12px',
    fontWeight: 500,
    lineHeight: 1.4,
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
  card: '0 1px 2px rgba(0,0,0,.04), 0 12px 32px rgba(0,0,0,.06)',
  elevated: '0 2px 4px rgba(0,0,0,.04), 0 16px 40px rgba(0,0,0,.08)',
  sidebar: '1px 0 0 rgba(0,0,0,.06)',
} as const;

export const radii = {
  card: '20px',
  button: '8px',
  pill: '9999px',
  input: '8px',
} as const;

export const motion = {
  pageTransition: '200ms',
  sidebar: '200ms',
  cardReveal: '150ms',
  activityUpdate: '150ms',
  easing: 'cubic-bezier(0.16, 1, 0.3, 1)',
} as const;
