// RAGMODEX Glass — design tokens
// Single source of truth. Do not duplicate these values inline.

export const TOKENS = {
  // Type
  fontDisplay: '"Inter", -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", system-ui, sans-serif',
  fontText: '"Inter", -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", system-ui, sans-serif',
  fontMono: '"SF Mono", ui-monospace, "JetBrains Mono", Menlo, monospace',

  // Foreground
  ink: '#0e1014',
  inkSoft: '#2a2d35',
  inkMuted: '#6b6f7a',
  inkFaint: '#9ea3ad',

  // Surface (glass)
  glassA: 'rgba(255, 255, 255, 0.62)',
  glassB: 'rgba(255, 255, 255, 0.45)',
  glassC: 'rgba(255, 255, 255, 0.30)',
  glassEdge: 'rgba(255, 255, 255, 0.85)',
  glassBorder: 'rgba(15, 18, 28, 0.06)',
  glassDivider: 'rgba(15, 18, 28, 0.07)',

  // Accent — sage/green
  accent: 'oklch(66% 0.115 155)',
  accentSoft: 'oklch(92% 0.04 155)',
  accentInk: 'oklch(38% 0.085 155)',

  // Secondary accent
  blue: 'oklch(66% 0.115 240)',
  blueSoft: 'oklch(94% 0.025 240)',

  // Radii
  r4: 6, r3: 10, r2: 14, r1: 20, r0: 28, pill: 999,

  // Shadows
  shadowFloat: '0 1px 0 rgba(255,255,255,0.6) inset, 0 0 0 1px rgba(15,18,28,0.05), 0 8px 24px -8px rgba(15,18,28,0.10), 0 28px 60px -20px rgba(15,18,28,0.12)',
  shadowCard: '0 1px 0 rgba(255,255,255,0.7) inset, 0 0 0 1px rgba(15,18,28,0.05), 0 6px 18px -8px rgba(15,18,28,0.08)',
  shadowInput: '0 1px 0 rgba(255,255,255,0.7) inset, 0 0 0 1px rgba(15,18,28,0.06)',
  shadowPress: '0 1px 0 rgba(255,255,255,0.6) inset, 0 0 0 1px rgba(15,18,28,0.06), 0 4px 10px -4px rgba(15,18,28,0.10)',
};
