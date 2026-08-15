export const colors = {
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
  white: '#FFFFFF',
};

export const typography = {
  hero: { fontSize: 56, fontWeight: '700' as const, letterSpacing: -1.2 },
  title: { fontSize: 22, fontWeight: '700' as const, letterSpacing: -0.3 },
  subtitle: { fontSize: 17, fontWeight: '600' as const },
  body: { fontSize: 16, fontWeight: '400' as const, lineHeight: 22 },
  cue: { fontSize: 15, fontWeight: '600' as const, lineHeight: 20 },
  caption: { fontSize: 13, fontWeight: '500' as const, lineHeight: 18 },
  label: { fontSize: 13, fontWeight: '700' as const, letterSpacing: 0.2 },
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

export const radii = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
};

export const grid = {
  columns: 4,
  gap: 8,
  padding: 16,
};
