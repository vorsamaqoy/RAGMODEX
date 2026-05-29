// RAGMODEX Glass — shared atoms
// Reused across multiple pages: Tab, ButtonPrimary, ButtonGhost, Toggle, MetricTile.

import { TOKENS } from './tokens';
import { Icon, Label } from './primitives';
import { useAppStore } from '../store';

/* ---------- Top-bar tab ---------- */
export const Tab = ({ icon, label, active, dot }) => {
  const modelLoaded = useAppStore(s => s.modelLoaded);
  const trainingData = useAppStore(s => s.trainingData);
  const isStatusTab = label === 'Model' || label === 'Dataset';
  const isLoaded = label === 'Model' ? modelLoaded : label === 'Dataset' ? trainingData : true;
  const statusColor = isLoaded ? TOKENS.accent : 'oklch(60% 0.16 25)';
  const statusBg = isLoaded ? 'oklch(66% 0.115 155 / 0.12)' : 'oklch(70% 0.16 25 / 0.12)';
  const statusRing = isLoaded ? 'oklch(66% 0.115 155 / 0.22)' : 'oklch(70% 0.16 25 / 0.24)';
  return (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 9,
    padding: '8px 14px 8px 11px',
    borderRadius: 12,
    background: isStatusTab ? statusBg : active ? '#fff' : 'transparent',
    color: active ? TOKENS.ink : TOKENS.inkMuted,
    fontFamily: TOKENS.fontText, fontSize: 13.5, fontWeight: 600, letterSpacing: '-0.005em',
    boxShadow: isStatusTab ? `0 1px 0 rgba(255,255,255,0.8) inset, 0 0 0 1px ${statusRing}` : active ? '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.05), 0 4px 12px -6px rgba(15,18,28,0.10)' : 'none',
    cursor: 'pointer',
  }}>
    <span style={{ color: isStatusTab ? statusColor : active ? TOKENS.accent : TOKENS.inkFaint, display: 'flex' }}>
      <Icon name={icon} size={15} />
    </span>
    {label}
    {(dot || isStatusTab) && <span title={isLoaded ? `${label} loaded` : `${label} not loaded`} style={{ width: 6, height: 6, borderRadius: 999, background: statusColor, marginLeft: 2 }}/>}
  </div>
  );
};

/* ---------- Buttons ---------- */
export const ButtonPrimary = ({ icon, children, full, disabled, onClick }) => (
  <button type="button" disabled={disabled} onClick={onClick} style={{
    appearance: 'none', border: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    height: 44, padding: full ? '0 22px' : '0 18px', width: full ? '100%' : 'auto',
    borderRadius: 13,
    background: `linear-gradient(180deg, oklch(70% 0.13 155), oklch(58% 0.13 155))`,
    color: '#fff',
    fontFamily: TOKENS.fontText, fontSize: 14, fontWeight: 600, letterSpacing: '-0.005em',
    boxShadow: '0 1px 0 rgba(255,255,255,0.35) inset, 0 0 0 1px oklch(48% 0.13 155 / 0.5), 0 6px 14px -4px oklch(50% 0.13 155 / 0.45)',
    opacity: disabled ? 0.55 : 1,
  }}>
    {icon && <Icon name={icon} size={16}/>}
    {children}
  </button>
);

export const ButtonGhost = ({ icon, children, disabled, onClick }) => (
  <button type="button" disabled={disabled} onClick={onClick} style={{
    appearance: 'none', cursor: disabled ? 'not-allowed' : 'pointer', border: 'none',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    height: 40, padding: '0 16px',
    borderRadius: 12,
    background: 'rgba(255,255,255,0.6)',
    color: TOKENS.ink,
    fontFamily: TOKENS.fontText, fontSize: 13.5, fontWeight: 600, letterSpacing: '-0.005em',
    boxShadow: TOKENS.shadowInput,
    backdropFilter: 'blur(20px)',
    opacity: disabled ? 0.55 : 1,
  }}>
    {icon && <span style={{ color: TOKENS.accent, display: 'flex' }}><Icon name={icon} size={15}/></span>}
    {children}
  </button>
);

/* ---------- Toggle ---------- */
export const Toggle = ({ on = true }) => (
  <div style={{
    width: 40, height: 22, borderRadius: 999,
    background: on ? `linear-gradient(180deg, oklch(70% 0.13 155), oklch(58% 0.13 155))` : 'rgba(15,18,28,0.15)',
    position: 'relative',
    boxShadow: on ? '0 0 0 1px oklch(48% 0.13 155 / 0.4), 0 2px 6px -2px oklch(50% 0.13 155 / 0.4)' : 'inset 0 1px 2px rgba(15,18,28,0.1)',
    transition: 'all .2s ease',
  }}>
    <div style={{
      position: 'absolute', top: 2, left: on ? 20 : 2,
      width: 18, height: 18, borderRadius: 999, background: '#fff',
      boxShadow: '0 1px 3px rgba(15,18,28,0.25)',
      transition: 'left .2s ease',
    }}/>
  </div>
);

/* ---------- Metric tile ---------- */
export const MetricTile = ({ label, value, sub, tone = 'neutral', tiny }) => {
  const tones = {
    accent:   { color: 'oklch(40% 0.1 155)',  bg: 'linear-gradient(180deg, oklch(96% 0.045 155 / 0.85), oklch(94% 0.045 155 / 0.6))', ring: 'oklch(66% 0.115 155 / 0.22)' },
    danger:   { color: 'oklch(45% 0.16 25)',  bg: 'linear-gradient(180deg, oklch(95% 0.04 25 / 0.7), oklch(93% 0.04 25 / 0.55))',    ring: 'oklch(70% 0.16 25 / 0.22)' },
    neutral:  { color: TOKENS.ink,            bg: 'rgba(255,255,255,0.55)',                                                          ring: 'rgba(15,18,28,0.06)' },
    info:     { color: 'oklch(40% 0.12 245)', bg: 'linear-gradient(180deg, oklch(95% 0.04 245 / 0.7), oklch(93% 0.04 245 / 0.55))', ring: 'oklch(66% 0.115 245 / 0.22)' },
  }[tone];
  return (
    <div style={{
      flex: 1,
      padding: '20px 22px',
      background: tones.bg,
      backdropFilter: 'blur(40px) saturate(180%)',
      borderRadius: 18,
      boxShadow: `0 1px 0 rgba(255,255,255,0.8) inset, 0 0 0 1px ${tones.ring}, 0 6px 16px -10px rgba(15,18,28,0.10)`,
      display: 'flex', flexDirection: 'column', gap: 6,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Label>{label}</Label>
        {tiny && <span style={{ fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkFaint }}>{tiny}</span>}
      </div>
      <div style={{
        fontFamily: TOKENS.fontDisplay, fontSize: 42, fontWeight: 700,
        color: tones.color, letterSpacing: '-0.03em', lineHeight: 1,
      }}>{value}</div>
      {sub && <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted }}>{sub}</div>}
    </div>
  );
};
