// RAGMODEX Glass — primitives
// MeshBackground, Glass card, Label, Caption, Icon set.

import { TOKENS } from './tokens';

/* ---------- Mesh background ---------- */
export const MeshBackground = ({ children, style }) => (
  <div style={{
    position: 'relative',
    width: '100%',
    height: '100%',
    background:
      `radial-gradient(60% 50% at 12% 8%, oklch(94% 0.06 155 / 0.55), transparent 60%),
       radial-gradient(40% 35% at 90% 0%, oklch(92% 0.06 28 / 0.55), transparent 65%),
       radial-gradient(55% 50% at 100% 100%, oklch(92% 0.05 245 / 0.60), transparent 60%),
       radial-gradient(45% 40% at 0% 100%, oklch(94% 0.05 130 / 0.50), transparent 60%),
       linear-gradient(180deg, #f4f5f7 0%, #eef0f4 100%)`,
    overflow: 'hidden',
    ...style,
  }}>
    <div style={{
      position: 'absolute', inset: 0, pointerEvents: 'none',
      opacity: 0.5, mixBlendMode: 'overlay',
      backgroundImage: `url("data:image/svg+xml;utf8,<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.5 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")`,
    }} />
    {children}
  </div>
);

/* ---------- Glass card ---------- */
export const Glass = ({ tone = 'A', radius = TOKENS.r1, padding = 20, style, children, onClick }) => {
  const bg = tone === 'B' ? TOKENS.glassB : tone === 'C' ? TOKENS.glassC : TOKENS.glassA;
  return (
    <div onClick={onClick} style={{
      position: 'relative',
      background: bg,
      backdropFilter: 'blur(40px) saturate(180%)',
      WebkitBackdropFilter: 'blur(40px) saturate(180%)',
      borderRadius: radius,
      padding,
      boxShadow: TOKENS.shadowCard,
      color: TOKENS.ink,
      transition: 'transform .25s ease, box-shadow .25s ease',
      cursor: onClick ? 'pointer' : 'default',
      ...style,
    }}>
      {children}
    </div>
  );
};

/* ---------- Atoms ---------- */
export const Label = ({ children, style }) => (
  <div style={{
    fontFamily: TOKENS.fontText,
    fontSize: 10.5,
    fontWeight: 600,
    letterSpacing: '0.10em',
    textTransform: 'uppercase',
    color: TOKENS.inkMuted,
    ...style,
  }}>{children}</div>
);

export const Caption = ({ children, style }) => (
  <div style={{ fontFamily: TOKENS.fontText, fontSize: 13, color: TOKENS.inkMuted, lineHeight: 1.5, ...style }}>
    {children}
  </div>
);

/* ---------- Icons (line, monochrome, 1.5 stroke) ---------- */
export const Icon = ({ name, size = 18, color = 'currentColor', stroke = 1.6 }) => {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: color, strokeWidth: stroke, strokeLinecap: 'round', strokeLinejoin: 'round' };
  switch (name) {
    case 'chat': return <svg {...common}><path d="M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12Z"/></svg>;
    case 'flask': return <svg {...common}><path d="M9 3h6M10 3v6L5 19a2 2 0 0 0 1.7 3h10.6A2 2 0 0 0 19 19l-5-10V3"/><path d="M7.5 14h9"/></svg>;
    case 'layers': return <svg {...common}><path d="M12 3 2 8l10 5 10-5-10-5Z"/><path d="m2 16 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>;
    case 'search': return <svg {...common}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>;
    case 'chart': return <svg {...common}><path d="M4 20V6"/><path d="M10 20v-8"/><path d="M16 20v-4"/><path d="M22 20H2"/></svg>;
    case 'sparkle': return <svg {...common}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.5 5.5l2.8 2.8M15.7 15.7l2.8 2.8M5.5 18.5l2.8-2.8M15.7 8.3l2.8-2.8"/></svg>;
    case 'gear': return <svg {...common}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.6 1.7 1.7 0 0 0-1.8.3l-.1.1A2 2 0 1 1 4.3 16.9l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.6-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1A2 2 0 1 1 7.1 4.3l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/></svg>;
    case 'db': return <svg {...common}><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></svg>;
    case 'cpu': return <svg {...common}><rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/></svg>;
    case 'sliders': return <svg {...common}><path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/></svg>;
    case 'upload': return <svg {...common}><path d="M12 16V4"/><path d="m6 10 6-6 6 6"/><path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>;
    case 'file': return <svg {...common}><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/></svg>;
    case 'check': return <svg {...common}><path d="m5 12 5 5L20 7"/></svg>;
    case 'checkCircle': return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>;
    case 'x': return <svg {...common}><path d="M6 6l12 12M18 6 6 18"/></svg>;
    case 'xCircle': return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/></svg>;
    case 'chevDown': return <svg {...common}><path d="m6 9 6 6 6-6"/></svg>;
    case 'chevRight': return <svg {...common}><path d="m9 6 6 6-6 6"/></svg>;
    case 'sidebar': return <svg {...common}><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>;
    case 'info': return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 8v.01M11 12h1v5h1"/></svg>;
    case 'plus': return <svg {...common}><path d="M12 5v14M5 12h14"/></svg>;
    case 'dot': return <svg {...common} fill={color} stroke="none"><circle cx="12" cy="12" r="4"/></svg>;
    default: return null;
  }
};
