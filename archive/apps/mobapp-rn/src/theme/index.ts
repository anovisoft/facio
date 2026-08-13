/** Facio color tokens — calm green accent, not purple-AI default. */

export type ThemeMode = 'system' | 'light' | 'dark';

export type ColorPalette = {
  background: string;
  surface: string;
  surfaceMuted: string;
  primary: string;
  primaryPressed: string;
  text: string;
  textSecondary: string;
  textMuted: string;
  border: string;
  error: string;
  success: string;
  white: string;
  black: string;
  overlay: string;
  fabFallback: string;
  fabIcon: string;
};

export const lightColors: ColorPalette = {
  background: '#F7F4EF',
  surface: '#FFFFFF',
  surfaceMuted: '#EFEAE2',
  primary: '#1F4D3A',
  primaryPressed: '#163828',
  text: '#1A1A18',
  textSecondary: '#5C5A55',
  textMuted: '#8A8780',
  border: '#DDD6CB',
  error: '#B42318',
  success: '#1F4D3A',
  white: '#FFFFFF',
  black: '#000000',
  overlay: 'rgba(26, 26, 24, 0.45)',
  fabFallback: 'rgba(255, 255, 255, 0.72)',
  fabIcon: '#1A1A18',
};

export const darkColors: ColorPalette = {
  background: '#121411',
  surface: '#1C1F1B',
  surfaceMuted: '#262A25',
  primary: '#7CB89A',
  primaryPressed: '#5F9A7C',
  text: '#F2F0EA',
  textSecondary: '#A8A59C',
  textMuted: '#6F6C64',
  border: '#333830',
  error: '#F97066',
  success: '#7CB89A',
  white: '#FFFFFF',
  black: '#000000',
  overlay: 'rgba(0, 0, 0, 0.55)',
  fabFallback: 'rgba(28, 31, 27, 0.78)',
  fabIcon: '#F2F0EA',
};

export const typography = {
  hero: { fontSize: 28, fontWeight: '700' as const, letterSpacing: -0.4 },
  title: { fontSize: 22, fontWeight: '700' as const, letterSpacing: -0.3 },
  subtitle: { fontSize: 17, fontWeight: '600' as const },
  body: { fontSize: 16, fontWeight: '400' as const, lineHeight: 24 },
  caption: { fontSize: 13, fontWeight: '500' as const, lineHeight: 18 },
  label: { fontSize: 12, fontWeight: '600' as const, letterSpacing: 0.4 },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
} as const;
