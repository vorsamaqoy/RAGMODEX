import { useMemo, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { TOKENS, MeshBackground, Glass, Label, Caption, Icon, Tab, ButtonGhost, Toggle } from '../glass';
import { getMoleculeDiff, moleculeImageUrl, runDesign } from '../lib/api';
import { GlassLlmModelSelect } from '../components/GlassLlmModelSelect';
import { GlassSettingsShortcut } from '../components/GlassSettingsShortcut';

/* RAGMODEX Glass - Molecular Design page artboard */

/* ---------- Local sidebar with Design active ---------- */
const DesignSidebar = () => {
  const items = [
    { i: 'chat', l: 'Chat' },
    { i: 'flask', l: 'Prediction' },
    { i: 'layers', l: 'Design', active: true },
    { i: 'search', l: 'Screening' },
    { i: 'chart', l: 'Evaluation' },
    { i: 'sparkle', l: 'Visualizer' },
  ];
  return (
    <div data-glass-sidebar style={{ width: 230, flex: '0 0 230px', padding: 14, display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 8px 18px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <img
            src="/logo_ragmodex.png?v=20260524"
            alt="RAGMODEX"
            style={{ width: 30, height: 30, borderRadius: 9, objectFit: 'contain', flexShrink: 0 }}
          />
          <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 14.5, fontWeight: 700, letterSpacing: '-0.01em', color: TOKENS.ink }}>RAGMODEX</div>
        </div>
        <div style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="sidebar" size={16}/></div>
      </div>

      {items.map((it, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '9px 12px',
          borderRadius: 12,
          background: it.active ? 'rgba(255,255,255,0.7)' : 'transparent',
          boxShadow: it.active ? '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.05), 0 4px 12px -6px rgba(15,18,28,0.10)' : 'none',
          color: it.active ? TOKENS.ink : TOKENS.inkSoft,
          fontFamily: TOKENS.fontText, fontSize: 13.5, fontWeight: it.active ? 600 : 500, letterSpacing: '-0.005em',
        }}>
          <span style={{ color: it.active ? TOKENS.accent : TOKENS.inkMuted, display: 'flex' }}>
            <Icon name={it.i} size={17}/>
          </span>
          {it.l}
        </div>
      ))}

      <div style={{ flex: 1 }}/>

      <GlassSettingsShortcut/>
    </div>
  );
};

/* ---------- Top bar with Design breadcrumb ---------- */
const DesignTopBar = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 24px 14px 12px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: TOKENS.fontText, fontSize: 13.5, color: TOKENS.inkMuted }}>
      <span>RAGMODEX</span>
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={14}/></span>
      <span style={{ color: TOKENS.ink, fontWeight: 600 }}>Design</span>
    </div>

    <Glass tone="B" radius={14} padding={4} style={{ display: 'flex', gap: 2 }}>
      <Tab icon="cpu" label="Model" active dot/>
      <Tab icon="db" label="Dataset" dot/>
      <GlassLlmModelSelect/>
    </Glass>
  </div>
);

/* ---------- Small atoms ---------- */
const NumField = ({ label, value, hint, min = 1, max = 100, step = 1, onChange }) => {
  const clamp = (next) => Math.min(max, Math.max(min, next));
  const setValue = (next) => onChange?.(clamp(next));

  return (
  <div>
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
      <Label>{label}</Label>
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}>
        <Icon name="info" size={12}/>
      </span>
    </div>
    <div style={{
      display: 'flex', alignItems: 'center',
      height: 44, padding: '0 4px 0 14px',
      background: 'rgba(255,255,255,0.55)',
      backdropFilter: 'blur(20px) saturate(160%)',
      borderRadius: 12,
      boxShadow: TOKENS.shadowInput,
    }}>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={event => {
          const next = Number(event.target.value);
          if (!Number.isNaN(next)) setValue(next);
        }}
        style={{
          flex: 1,
          minWidth: 0,
          border: 'none',
          outline: 'none',
          background: 'transparent',
          fontFamily: TOKENS.fontMono,
          fontSize: 16,
          color: TOKENS.ink,
          fontWeight: 600,
        }}
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '2px 4px' }}>
        <button type="button" onClick={() => setValue(Number(value) + step)} style={{ appearance: 'none', border: 'none', background: 'rgba(15,18,28,0.04)', width: 22, height: 18, borderRadius: 6, display: 'grid', placeItems: 'center', cursor: 'pointer', color: TOKENS.inkMuted }}>
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 7 3-3 3 3"/></svg>
        </button>
        <button type="button" onClick={() => setValue(Number(value) - step)} style={{ appearance: 'none', border: 'none', background: 'rgba(15,18,28,0.04)', width: 22, height: 18, borderRadius: 6, display: 'grid', placeItems: 'center', cursor: 'pointer', color: TOKENS.inkMuted }}>
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 5 3 3 3-3"/></svg>
        </button>
      </div>
    </div>
    {hint && <div style={{ marginTop: 6, fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkFaint }}>{hint}</div>}
  </div>
  );
};


/* ---------- MMR Weights triangle widget ---------- */
const MMRWidget = ({ mode = 'balanced', weights, onPreset, onWeightsChange }) => {
  const vertices = {
    ad: { x: 70, y: 18 },
    activity: { x: 18, y: 108 },
    diversity: { x: 122, y: 108 },
  };
  const current = weights ?? { wActivity: 0.5, wDiversity: 0.25, wAd: 0.25 };
  const pt = {
    x: current.wAd * vertices.ad.x + current.wActivity * vertices.activity.x + current.wDiversity * vertices.diversity.x,
    y: current.wAd * vertices.ad.y + current.wActivity * vertices.activity.y + current.wDiversity * vertices.diversity.y,
  };
  const applyClick = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * 140;
    const py = ((event.clientY - rect.top) / rect.height) * 130;
    const wAdRaw = Math.max(0, Math.min(1, (108 - py) / (108 - 18)));
    const leftX = vertices.activity.x + wAdRaw * (vertices.ad.x - vertices.activity.x);
    const rightX = vertices.diversity.x + wAdRaw * (vertices.ad.x - vertices.diversity.x);
    const row = rightX === leftX ? 0.5 : Math.max(0, Math.min(1, (px - leftX) / (rightX - leftX)));
    const rem = 1 - wAdRaw;
    const raw = {
      wActivity: rem * (1 - row),
      wDiversity: rem * row,
      wAd: wAdRaw,
    };
    const snap = (value) => Math.round(value * 20) / 20;
    let next = {
      wActivity: snap(raw.wActivity),
      wDiversity: snap(raw.wDiversity),
      wAd: snap(raw.wAd),
    };
    const sum = next.wActivity + next.wDiversity + next.wAd || 1;
    next = {
      wActivity: next.wActivity / sum,
      wDiversity: next.wDiversity / sum,
      wAd: next.wAd / sum,
    };
    onWeightsChange?.(next);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <Label>MMR Weights</Label>
      <div style={{
        position: 'relative',
        background: 'rgba(255,255,255,0.5)',
        backdropFilter: 'blur(20px) saturate(160%)',
        borderRadius: 14,
        boxShadow: TOKENS.shadowInput,
        padding: 14,
      }}>
        <svg onClick={applyClick} viewBox="0 0 140 130" width="100%" height={140} style={{ display: 'block', cursor: 'crosshair' }}>
          {/* Triangle */}
          <defs>
            <linearGradient id="triFill" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stopColor="oklch(66% 0.115 155 / 0.18)"/>
              <stop offset="100%" stopColor="oklch(66% 0.115 240 / 0.10)"/>
            </linearGradient>
          </defs>
          <polygon points="70,18 18,108 122,108" fill="url(#triFill)" stroke="rgba(15,18,28,0.18)" strokeWidth="1"/>
          {/* Centroid dashed lines */}
          <line x1="70" y1="78" x2="70" y2="18" stroke="rgba(15,18,28,0.10)" strokeWidth="0.8" strokeDasharray="2 3"/>
          <line x1="70" y1="78" x2="18" y2="108" stroke="rgba(15,18,28,0.10)" strokeWidth="0.8" strokeDasharray="2 3"/>
          <line x1="70" y1="78" x2="122" y2="108" stroke="rgba(15,18,28,0.10)" strokeWidth="0.8" strokeDasharray="2 3"/>
          {/* Vertex labels */}
          <text x="70" y="13" textAnchor="middle" fontSize="7.5" fontFamily={TOKENS.fontText} fontWeight="600" fill="#0e1014">AD Score</text>
          <text x="70" y="6" textAnchor="middle" fontSize="6" fontFamily={TOKENS.fontMono} fill="#6b6f7a">33%</text>
          <text x="14" y="118" textAnchor="middle" fontSize="7.5" fontFamily={TOKENS.fontText} fontWeight="600" fill="#0e1014">Activity</text>
          <text x="14" y="126" textAnchor="middle" fontSize="6" fontFamily={TOKENS.fontMono} fill="#6b6f7a">33%</text>
          <text x="126" y="118" textAnchor="middle" fontSize="7.5" fontFamily={TOKENS.fontText} fontWeight="600" fill="#0e1014">Diversity</text>
          <text x="126" y="126" textAnchor="middle" fontSize="6" fontFamily={TOKENS.fontMono} fill="#6b6f7a">33%</text>
          {/* Current weight dot */}
          <circle cx={pt.x} cy={pt.y} r="7" fill="oklch(66% 0.115 155 / 0.18)"/>
          <circle cx={pt.x} cy={pt.y} r="3.5" fill="oklch(60% 0.13 155)" stroke="#fff" strokeWidth="1.4"/>
        </svg>
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: 6,
        fontFamily: TOKENS.fontMono,
        fontSize: 10.5,
        color: TOKENS.inkMuted,
      }}>
        <div>Act {(current.wActivity * 100).toFixed(0)}%</div>
        <div>Div {(current.wDiversity * 100).toFixed(0)}%</div>
        <div>AD {(current.wAd * 100).toFixed(0)}%</div>
      </div>
      {/* Segmented control */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
        {['Activity', 'Balanced', 'Diversity'].map((l) => {
          const active = l.toLowerCase() === mode;
          return (
            <button key={l} type="button" onClick={() => onPreset?.(l.toLowerCase())} style={{
              appearance: 'none', border: 'none',
              height: 32, display: 'grid', placeItems: 'center',
              borderRadius: 9,
              background: active ? `linear-gradient(180deg, oklch(70% 0.13 155), oklch(58% 0.13 155))` : 'rgba(255,255,255,0.6)',
              color: active ? '#fff' : TOKENS.inkSoft,
              fontFamily: TOKENS.fontText, fontSize: 12.5, fontWeight: 600, letterSpacing: '-0.005em',
              boxShadow: active
                ? '0 1px 0 rgba(255,255,255,0.3) inset, 0 0 0 1px oklch(48% 0.13 155 / 0.4), 0 4px 10px -3px oklch(50% 0.13 155 / 0.35)'
                : '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px rgba(15,18,28,0.06)',
              cursor: 'pointer',
            }}>{l}</button>
          );
        })}
      </div>
    </div>
  );
};

/* ---------- Candidate card ---------- */
const MoleculeSVG = ({ seed = 1 }) => {
  // Stylized molecule placeholder using consistent palette
  const variants = [
    { atoms: [['Cl', 0.21, 0.32, '#54b257'], ['Cl', 0.41, 0.32, '#54b257'], ['F', 0.27, 0.62, '#5fb0d6'], ['O', 0.42, 0.48, '#e08856']] },
    { atoms: [['Cl', 0.20, 0.32, '#54b257'], ['F', 0.13, 0.45, '#5fb0d6'], ['Cl', 0.22, 0.55, '#54b257'], ['Cl', 0.42, 0.32, '#54b257'], ['O', 0.42, 0.48, '#e08856']] },
    { atoms: [['F', 0.13, 0.45, '#5fb0d6'], ['Cl', 0.42, 0.32, '#54b257'], ['I', 0.27, 0.28, '#a87bd0'], ['F', 0.21, 0.55, '#5fb0d6'], ['O', 0.42, 0.48, '#e08856']] },
  ];
  const v = variants[(seed - 1) % variants.length];
  // Lines describing carbon skeleton (4 zig-zag bonds going right)
  return (
    <svg viewBox="0 0 300 170" width="100%" height="100%" style={{ display: 'block' }}>
      {/* Bonds */}
      <g stroke="#0e1014" strokeWidth="2.2" fill="none" strokeLinecap="round">
        {/* zig-zag from (60,85) to (270,85) */}
        <path d="M60 85 L90 65 L120 85 L150 65 L180 85 L210 65 L240 85 L270 65"/>
        {/* branch up-left at start */}
        <path d="M60 85 L45 60"/>
        <path d="M60 85 L45 110"/>
        {/* branch from second carbon */}
        <path d="M90 65 L80 40"/>
        <path d="M90 65 L100 40"/>
        {/* O connector */}
        <path d="M120 85 L130 100"/>
      </g>
      {/* Atom labels */}
      {[
        ['F', 38, 60, '#5fb0d6'],
        ['F', 38, 118, '#5fb0d6'],
        ['Cl', 70, 36, '#3fb557'],
        ['Cl', 108, 36, '#3fb557'],
        ['O', 135, 110, '#e08856'],
      ].slice(0, seed === 3 ? 5 : seed === 2 ? 5 : 4).map(([lbl, x, y, c], i) => (
        <g key={i}>
          <rect x={x - 11} y={y - 11} width={lbl === 'Cl' ? 22 : 18} height="20" rx="3" fill="#fff"/>
          <text x={x} y={y + 5} textAnchor="middle" fontSize="14" fontWeight="700" fontFamily={TOKENS.fontDisplay} fill={c}>{lbl}</text>
        </g>
      ))}
      {/* Iodine on #3 */}
      {seed === 3 && (
        <g>
          <rect x="74" y="29" width="14" height="20" rx="3" fill="#fff"/>
          <text x="81" y="45" textAnchor="middle" fontSize="14" fontWeight="700" fontFamily={TOKENS.fontDisplay} fill="#a87bd0">I</text>
        </g>
      )}
    </svg>
  );
};

const CandidateCard = ({ idx, delta, pActive, ad, atoms = [], smiles }) => (
  <Glass tone="A" radius={22} padding={0} style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
    {/* Top bar */}
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '12px 14px',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '4px 10px 4px 6px',
        background: 'oklch(66% 0.115 155 / 0.14)',
        borderRadius: 999,
        fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 700, color: TOKENS.accentInk,
      }}>
        <span style={{
          width: 18, height: 18, borderRadius: 999, background: '#fff',
          display: 'grid', placeItems: 'center', fontFamily: TOKENS.fontMono, fontSize: 10, color: TOKENS.accentInk, fontWeight: 700,
          boxShadow: '0 0 0 1px oklch(66% 0.115 155 / 0.3)',
        }}>#{idx}</span>
        Rank {idx}
      </div>
      <div style={{
        padding: '4px 10px',
        background: 'rgba(15,18,28,0.05)',
        borderRadius: 8,
        fontFamily: TOKENS.fontMono, fontSize: 11.5, color: TOKENS.inkMuted, fontWeight: 600,
      }}>AD {ad}</div>
    </div>

    {/* Molecule */}
    <div style={{
      margin: '0 14px',
      background: 'linear-gradient(180deg, rgba(255,255,255,0.85), rgba(255,255,255,0.55))',
      borderRadius: 16,
      boxShadow: '0 1px 0 rgba(255,255,255,0.95) inset, 0 0 0 1px rgba(15,18,28,0.05)',
      aspectRatio: '300/170',
      display: 'grid', placeItems: 'center',
      overflow: 'hidden',
    }}>
      {smiles ? (
        <img
          src={moleculeImageUrl(smiles, 360, 200)}
          alt={smiles}
          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
          loading="lazy"
          decoding="async"
        />
      ) : (
        <MoleculeSVG seed={idx}/>
      )}
    </div>

    {/* Stats */}
    <div style={{ padding: '14px 16px 8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 10px',
          background: 'oklch(66% 0.115 155 / 0.14)',
          color: TOKENS.accentInk,
          borderRadius: 999,
          fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 700,
        }}>
          <svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 9l4-5 3 3 3-5"/><path d="M8 2h3v3"/></svg>
          +{delta}%
        </div>
        <div style={{ fontFamily: TOKENS.fontMono, fontSize: 22, fontWeight: 700, color: TOKENS.ink, letterSpacing: '-0.02em' }}>
          {pActive}<span style={{ fontSize: 14, color: TOKENS.inkMuted, fontWeight: 500 }}>%</span>
        </div>
      </div>
      <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted, marginBottom: 6 }}>P(active)</div>
      {/* Progress bar */}
      <div style={{ height: 6, background: 'rgba(15,18,28,0.06)', borderRadius: 999, position: 'relative', overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', inset: 0, width: `${pActive}%`,
          background: `linear-gradient(90deg, oklch(66% 0.115 155), oklch(74% 0.13 195))`,
          borderRadius: 999,
        }}/>
      </div>
    </div>

    {/* Transformations footer */}
    <div style={{
      margin: '10px 14px 14px',
      padding: '10px 12px',
      background: 'rgba(255,255,255,0.5)',
      borderRadius: 12,
      boxShadow: '0 1px 0 rgba(255,255,255,0.7) inset, 0 0 0 1px rgba(15,18,28,0.05)',
      display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
    }}>
      <span style={{ fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 600, color: TOKENS.inkMuted, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Î”</span>
      {atoms.map((a, i) => (
        <span key={i} style={{
          fontFamily: TOKENS.fontMono, fontSize: 11.5,
          color: a.startsWith('+') ? TOKENS.accentInk : TOKENS.inkSoft,
          fontWeight: 600,
        }}>{a}</span>
      ))}
    </div>
  </Glass>
);

/* ---------- Evolution path ---------- */
const TinyMolecule = ({ kind }) => {
  // Simple silhouettes that get progressively more complex
  const path = {
    base: 'M20 50 L40 30 L60 50',
    iter0: 'M15 50 L35 30 L55 50 L75 30',
    iter1: 'M15 50 L35 30 L55 50 L75 30 L95 50',
    iter2: 'M15 50 L35 30 L55 50 L75 30 L95 50 L115 30',
    iter3: 'M10 50 L30 30 L50 50 L70 30 L90 50 L110 30',
    iter4: 'M10 50 L30 30 L50 50 L70 30 L90 50 L110 30',
    iter5: 'M10 50 L30 30 L50 50 L70 30 L90 50 L110 30',
  };
  const showCl = ['iter1', 'iter2', 'iter3', 'iter4', 'iter5'].includes(kind);
  const showO = ['iter2', 'iter3', 'iter4', 'iter5'].includes(kind);
  const showF = ['iter3', 'iter4', 'iter5'].includes(kind);
  return (
    <svg viewBox="0 0 130 80" width="100%" height="100%">
      <path d={path[kind] || path.base} stroke="#0e1014" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      {showCl && <text x="74" y="25" fontSize="9" fontWeight="700" fontFamily={TOKENS.fontDisplay} fill="#3fb557">Cl</text>}
      {showO && <text x="56" y="58" fontSize="9" fontWeight="700" fontFamily={TOKENS.fontDisplay} fill="#e08856">O</text>}
      {showF && <text x="30" y="22" fontSize="9" fontWeight="700" fontFamily={TOKENS.fontDisplay} fill="#5fb0d6">F</text>}
    </svg>
  );
};

const EvoStep = ({ kind, p, ad, label, isBase, action }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, minWidth: 110 }}>
    <div style={{
      fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em',
      textTransform: 'uppercase', color: isBase ? TOKENS.inkMuted : TOKENS.accentInk,
    }}>{label}</div>
    <div style={{
      width: 110, height: 78,
      background: 'linear-gradient(180deg, rgba(255,255,255,0.85), rgba(255,255,255,0.55))',
      borderRadius: 12,
      boxShadow: isBase
        ? '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.06)'
        : '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px oklch(66% 0.115 155 / 0.22)',
      padding: 6,
    }}>
      <TinyMolecule kind={kind}/>
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
      <div style={{ fontFamily: TOKENS.fontMono, fontSize: 12, fontWeight: 700, color: TOKENS.ink }}>P = {p}%</div>
      {ad && <div style={{ fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkMuted }}>AD = {ad}</div>}
    </div>
    {!isBase && action && (
      <button type="button" onClick={() => window.alert('Candidate copied as the base molecule for the next run is planned; paste its SMILES into the base field for now.')} style={{
        appearance: 'none', border: 'none', cursor: 'pointer',
        padding: '4px 10px',
        background: 'rgba(255,255,255,0.7)',
        borderRadius: 7,
        fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 600, color: TOKENS.inkSoft, letterSpacing: '-0.005em',
        boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
      }}>Use as base</button>
    )}
  </div>
);

const EvoConnector = ({ formula, dir = 'add' }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', gap: 4, paddingTop: 32, minWidth: 56 }}>
    <span style={{ color: TOKENS.inkFaint, display: 'flex' }}>
      <Icon name="chevRight" size={20} stroke={1.8}/>
    </span>
    {formula && (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
      }}>
        {formula.map((f, i) => (
          <div key={i} style={{
            display: 'inline-flex', alignItems: 'center', gap: 3,
            padding: '2px 7px',
            background: f.sign === '+' ? 'oklch(94% 0.04 130 / 0.7)' : 'oklch(94% 0.04 28 / 0.7)',
            color: f.sign === '+' ? 'oklch(45% 0.1 145)' : 'oklch(48% 0.12 28)',
            borderRadius: 6,
            fontFamily: TOKENS.fontMono, fontSize: 10.5, fontWeight: 700,
            boxShadow: `0 0 0 1px ${f.sign === '+' ? 'oklch(70% 0.1 145 / 0.3)' : 'oklch(70% 0.12 28 / 0.3)'}`,
          }}>
            <span>{f.sign}</span>{f.label}
          </div>
        ))}
      </div>
    )}
  </div>
);

const RealDiffBadge = ({ smiA, smiB }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['mol-diff', smiA, smiB],
    queryFn: () => getMoleculeDiff(smiA, smiB),
    staleTime: Infinity,
    retry: false,
  });

  if (isLoading) {
    return (
      <div style={{ minWidth: 76, paddingTop: 62, display: 'grid', placeItems: 'start center', color: TOKENS.inkFaint }}>
        <Icon name="chevRight" size={20} stroke={1.8}/>
      </div>
    );
  }

  if (!data || data.scaffold_change) {
    return (
      <div style={{ minWidth: 88, paddingTop: 44, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
        <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={20} stroke={1.8}/></span>
        <span style={{
          padding: '3px 8px',
          borderRadius: 7,
          background: 'rgba(255,255,255,0.65)',
          color: TOKENS.inkMuted,
          fontFamily: TOKENS.fontText,
          fontSize: 10.5,
          fontWeight: 700,
          boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
        }}>scaffold change</span>
      </div>
    );
  }

  const added = data.added_frags.slice(0, 2);
  const removed = data.removed_frags.slice(0, 2);
  const addedLabels = (data.added_frag_labels ?? []).slice(0, 2);
  const removedLabels = (data.removed_frag_labels ?? []).slice(0, 2);
  const warning = data.fragment_render_warning ?? 'RDKit renders isolated fragments and may add implicit hydrogens; atom-delta labels omit those hydrogens.';
  const renderDelta = (kind, smi, index) => {
    const isAdd = kind === 'add';
    const label = isAdd ? addedLabels[index] ?? smi : removedLabels[index] ?? smi;
    return (
      <div key={`${kind}-${smi}-${index}`} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          padding: '2px 7px',
          borderRadius: 7,
          background: isAdd ? 'oklch(94% 0.04 130 / 0.72)' : 'oklch(94% 0.04 28 / 0.72)',
          color: isAdd ? TOKENS.accentInk : 'oklch(48% 0.12 28)',
          fontFamily: TOKENS.fontMono,
          fontSize: 11,
          fontWeight: 800,
          boxShadow: `0 0 0 1px ${isAdd ? 'oklch(70% 0.1 145 / 0.3)' : 'oklch(70% 0.12 28 / 0.3)'}`,
        }}>
          <span>{isAdd ? '+' : '-'}</span>{label}
          <span title={warning} style={{
            width: 14,
            height: 14,
            borderRadius: 999,
            display: 'inline-grid',
            placeItems: 'center',
            background: 'rgba(255,255,255,0.75)',
            color: TOKENS.inkMuted,
            fontFamily: TOKENS.fontText,
            fontSize: 10,
            fontWeight: 800,
            cursor: 'help',
          }}>?</span>
        </div>
        <img
          src={moleculeImageUrl(smi, 58, 40)}
          alt={`${isAdd ? '+' : '-'}${label}; RDKit isolated fragment ${smi}`}
          title={warning}
          loading="lazy"
          decoding="async"
          style={{ width: 58, height: 40, objectFit: 'contain', background: '#fff', borderRadius: 6, boxShadow: '0 0 0 1px rgba(15,18,28,0.06)' }}
        />
      </div>
    );
  };

  return (
    <div style={{ minWidth: 92, paddingTop: 18, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
      {added.map((smi, index) => renderDelta('add', smi, index))}
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={18} stroke={1.8}/></span>
      {removed.map((smi, index) => renderDelta('remove', smi, index))}
    </div>
  );
};

const RealEvolutionStep = ({ step, index, onUseAsBase }) => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, minWidth: 138 }}>
    <div style={{
      fontFamily: TOKENS.fontText,
      fontSize: 10.5,
      fontWeight: 700,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color: index === 0 ? TOKENS.inkMuted : TOKENS.accentInk,
    }}>{index === 0 ? 'Base' : `Iter ${step.iteration}`}</div>
    <div style={{
      width: 138,
      height: 92,
      background: 'linear-gradient(180deg, rgba(255,255,255,0.85), rgba(255,255,255,0.55))',
      borderRadius: 12,
      boxShadow: index === 0
        ? '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.06)'
        : '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px oklch(66% 0.115 155 / 0.22)',
      padding: 6,
    }}>
      <img
        src={moleculeImageUrl(step.best_smiles, 180, 120)}
        alt={step.best_smiles}
        loading="lazy"
        decoding="async"
        style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
      />
    </div>
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
      <div style={{ fontFamily: TOKENS.fontMono, fontSize: 12, fontWeight: 700, color: TOKENS.ink }}>
        P = {(step.best_prob * 100).toFixed(1)}%
      </div>
      {step.ad_score > 0 && (
        <div style={{ fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkMuted }}>
          AD = {step.ad_score.toFixed(2)}
        </div>
      )}
    </div>
    {index > 0 && (
      <button type="button" onClick={() => onUseAsBase(step.best_smiles)} style={{
        appearance: 'none', border: 'none', cursor: 'pointer',
        padding: '4px 10px',
        background: 'rgba(255,255,255,0.7)',
        borderRadius: 7,
        fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 600, color: TOKENS.inkSoft, letterSpacing: '-0.005em',
        boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
      }}>Use as base</button>
    )}
  </div>
);

const normaliseTimelineSteps = (result) => {
  const timeline = result?.timeline_path?.length ? result.timeline_path : (result?.history ?? []);
  const baseStep = {
    iteration: 0,
    best_smiles: result.base_smiles,
    best_prob: result.base_probability,
    ad_score: 0,
    n_generated: 0,
  };
  const includesBase = timeline[0]?.iteration === 0 || timeline[0]?.best_smiles === result.base_smiles;
  const steps = includesBase ? timeline : [baseStep, ...timeline];
  return steps
    .filter(step => step?.best_smiles)
    .map((step, index) => ({
      iteration: Number(step.iteration ?? index),
      best_smiles: String(step.best_smiles),
      best_prob: Number(step.best_prob ?? step.probability ?? 0),
      ad_score: Number(step.ad_score ?? 0),
      n_generated: Number(step.n_generated ?? 0),
    }));
};

const buildRunParams = (settings, weights) => ({
  iterations: settings.nIterations,
  beamSize: settings.beamSize,
  topK: settings.topK,
  patience: settings.patience,
  druglikeness: settings.useDruglikeness,
  mmrMode: settings.mmrMode,
  wActivity: weights.wActivity,
  wDiversity: weights.wDiversity,
  wAd: weights.wAd,
});

const flattenRunPoints = (runs) => {
  const points = [];
  runs.forEach((run, runIndex) => {
    run.steps.forEach((step, stepIndex) => {
      points.push({
        ...step,
        x: points.length,
        runNumber: runIndex + 1,
        stepIndex,
        runId: run.id,
        params: run.params,
      });
    });
  });
  return points;
};

const exportTextFile = async (filename, mime, text) => {
  const blob = new Blob([text], { type: mime });
  if (window.showSaveFilePicker) {
    const ext = filename.split('.').pop();
    const handle = await window.showSaveFilePicker({
      suggestedName: filename,
      types: [{ description: filename, accept: { [mime]: [`.${ext}`] } }],
    });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return;
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

const exportDesignRunsJson = (runs) => exportTextFile(
  'ragmodex-evolution-path.json',
  'application/json',
  JSON.stringify(runs, null, 2),
);

const exportDesignRunsCsv = (runs) => {
  const rows = [
    'run,step,iteration,smiles,p_active,ad_score,started_from,iterations,beam_size,top_k,patience,mode,w_activity,w_diversity,w_ad,druglikeness',
  ];
  runs.forEach((run, runIndex) => {
    run.steps.forEach((step, stepIndex) => {
      const params = run.params ?? {};
      rows.push([
        runIndex + 1,
        stepIndex,
        step.iteration,
        `"${String(step.best_smiles ?? '').replaceAll('"', '""')}"`,
        step.best_prob,
        step.ad_score ?? 0,
        `"${String(run.startedFrom ?? '').replaceAll('"', '""')}"`,
        params.iterations,
        params.beamSize,
        params.topK,
        params.patience,
        params.mmrMode,
        params.wActivity,
        params.wDiversity,
        params.wAd,
        params.druglikeness ? 'true' : 'false',
      ].join(','));
    });
  });
  return exportTextFile('ragmodex-evolution-path.csv', 'text/csv', rows.join('\n'));
};

const exportSvgAsPng = async (filename, svgText, width, height) => {
  const blob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const img = new Image();
  img.crossOrigin = 'anonymous';
  await new Promise((resolve, reject) => {
    img.onload = resolve;
    img.onerror = reject;
    img.src = url;
  });
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#f4f5f7';
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(img, 0, 0);
  URL.revokeObjectURL(url);
  const pngBlob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
  if (!pngBlob) return;
  if (window.showSaveFilePicker) {
    const handle = await window.showSaveFilePicker({
      suggestedName: filename,
      types: [{ description: 'PNG image', accept: { 'image/png': ['.png'] } }],
    });
    const writable = await handle.createWritable();
    await writable.write(pngBlob);
    await writable.close();
    return;
  }
  const pngUrl = URL.createObjectURL(pngBlob);
  const a = document.createElement('a');
  a.href = pngUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(pngUrl);
};

const buildExportSvg = (runs, width = 1280, height = 720) => {
  const points = flattenRunPoints(runs);
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' }[c]));
  const plotX = 70;
  const plotY = 82;
  const plotW = width - 130;
  const plotH = 250;
  const maxX = Math.max(1, points.length - 1);
  const xOf = (p) => plotX + (p.x / maxX) * plotW;
  const yProb = (p) => plotY + plotH - Math.max(0, Math.min(1, p.best_prob)) * plotH;
  const yAd = (p) => plotY + plotH - Math.max(0, Math.min(1, p.ad_score ?? 0)) * plotH;
  const probPath = points.map((p, i) => `${i ? 'L' : 'M'}${xOf(p).toFixed(1)},${yProb(p).toFixed(1)}`).join(' ');
  const adPath = points.map((p, i) => `${i ? 'L' : 'M'}${xOf(p).toFixed(1)},${yAd(p).toFixed(1)}`).join(' ');
  let cursorY = 390;
  const runBlocks = runs.map((run, runIndex) => {
    const params = run.params;
    const block = `
      <text x="70" y="${cursorY}" font-family="Inter, Arial" font-size="16" font-weight="700" fill="#0e1014">Run ${runIndex + 1}</text>
      <text x="150" y="${cursorY}" font-family="SF Mono, monospace" font-size="11" fill="#6b6f7a">start ${esc(run.startedFrom)} - iter ${params.iterations} - beam ${params.beamSize} - top ${params.topK} - patience ${params.patience} - ${params.mmrMode} - AD ${params.wAd.toFixed(2)} - drug ${params.druglikeness ? 'on' : 'off'}</text>
      ${run.steps.map((step, stepIndex) => {
        const x = 70 + stepIndex * 150;
        return `
          <rect x="${x}" y="${cursorY + 22}" width="126" height="82" rx="10" fill="#fff" stroke="#dfe3e8"/>
          <image href="${esc(moleculeImageUrl(step.best_smiles, 150, 96))}" x="${x + 8}" y="${cursorY + 28}" width="110" height="58" preserveAspectRatio="xMidYMid meet"/>
          <text x="${x + 8}" y="${cursorY + 96}" font-family="SF Mono, monospace" font-size="10" fill="#0e1014">P ${(step.best_prob * 100).toFixed(1)}% - AD ${(step.ad_score ?? 0).toFixed(2)}</text>
        `;
      }).join('')}
    `;
    cursorY += 134;
    return block;
  }).join('');

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
    <rect width="100%" height="100%" fill="#f4f5f7"/>
    <text x="70" y="42" font-family="Inter, Arial" font-size="24" font-weight="700" fill="#0e1014">RAGMODEX design path</text>
    <text x="70" y="62" font-family="Inter, Arial" font-size="12" fill="#6b6f7a">${runs.length} run${runs.length === 1 ? '' : 's'} - ${points.length} molecular states</text>
    <rect x="${plotX}" y="${plotY}" width="${plotW}" height="${plotH}" rx="16" fill="rgba(255,255,255,0.72)" stroke="#dfe3e8"/>
    ${[0, 0.25, 0.5, 0.75, 1].map(v => `<line x1="${plotX}" x2="${plotX + plotW}" y1="${plotY + plotH - v * plotH}" y2="${plotY + plotH - v * plotH}" stroke="#d7dce2" stroke-dasharray="3 5"/>`).join('')}
    ${runs.slice(0, -1).map((run, i) => {
      const boundary = runs.slice(0, i + 1).reduce((sum, r) => sum + r.steps.length, 0) - 0.5;
      const x = plotX + (boundary / maxX) * plotW;
      return `<line x1="${x}" x2="${x}" y1="${plotY}" y2="${plotY + plotH}" stroke="#9ea3ad" stroke-dasharray="6 6"/>`;
    }).join('')}
    <path d="${probPath}" fill="none" stroke="#2f9e64" stroke-width="3"/>
    <path d="${adPath}" fill="none" stroke="#d5a514" stroke-width="3"/>
    ${points.map(p => `<circle cx="${xOf(p)}" cy="${yProb(p)}" r="4" fill="${p.best_prob >= 0.5 ? '#2f9e64' : '#c94f4f'}"/><circle cx="${xOf(p)}" cy="${yAd(p)}" r="4" fill="#d5a514"/>`).join('')}
    <text x="${plotX + plotW - 180}" y="${plotY + 24}" font-family="Inter, Arial" font-size="12" fill="#2f9e64">P(active)</text>
    <text x="${plotX + plotW - 90}" y="${plotY + 24}" font-family="Inter, Arial" font-size="12" fill="#b88700">AD score</text>
    ${runBlocks}
  </svg>`;
};

const DesignPathPlot = ({ runs }) => {
  const [hovered, setHovered] = useState(null);
  const svgRef = useRef(null);
  const points = flattenRunPoints(runs);
  if (!points.length) return null;

  const width = 1040;
  const height = 310;
  const pad = { left: 54, right: 28, top: 28, bottom: 42 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const maxX = Math.max(1, points.length - 1);
  const xOf = (point) => pad.left + (point.x / maxX) * plotW;
  const yOf = (value) => pad.top + plotH - Math.max(0, Math.min(1, value)) * plotH;
  const lineFor = (selector) => points.map((point, index) => `${index ? 'L' : 'M'}${xOf(point)},${yOf(selector(point))}`).join(' ');

  const exportPath = async (format) => {
    const svgText = buildExportSvg(runs, 1280, Math.max(720, 390 + runs.length * 134));
    if (format === 'svg') {
      await exportTextFile('ragmodex-design-path.svg', 'image/svg+xml', svgText);
    } else {
      try {
        const pngSafeSvg = svgText.replace(/<image\\b[^>]*>/g, '');
        await exportSvgAsPng('ragmodex-design-path.png', pngSafeSvg, 1280, Math.max(720, 390 + runs.length * 134));
      } catch (error) {
        await exportTextFile('ragmodex-design-path.svg', 'image/svg+xml', svgText);
        window.alert('PNG export was blocked by the browser image renderer, so I saved the SVG version instead.');
      }
    }
  };

  return (
    <Glass tone="A" radius={26} padding={24} style={{ marginBottom: 22, overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>Cumulative path plot</div>
          <Caption style={{ marginTop: 3 }}>P(active) and AD score across all design runs.</Caption>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" onClick={() => exportPath('svg')} style={{ appearance: 'none', border: 'none', cursor: 'pointer', padding: '7px 12px', borderRadius: 10, background: 'rgba(255,255,255,0.68)', color: TOKENS.inkSoft, fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 700, boxShadow: TOKENS.shadowInput }}>Export SVG</button>
          <button type="button" onClick={() => exportPath('png')} style={{ appearance: 'none', border: 'none', cursor: 'pointer', padding: '7px 12px', borderRadius: 10, background: 'rgba(255,255,255,0.68)', color: TOKENS.inkSoft, fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 700, boxShadow: TOKENS.shadowInput }}>Export PNG</button>
        </div>
      </div>

      <div style={{ position: 'relative' }}>
        <svg ref={svgRef} viewBox={`0 0 ${width} ${height}`} width="100%" height={height} style={{ display: 'block' }}>
          <rect x={pad.left} y={pad.top} width={plotW} height={plotH} rx="14" fill="rgba(255,255,255,0.55)" stroke="rgba(15,18,28,0.06)"/>
          {[0, 0.25, 0.5, 0.75, 1].map(value => (
            <g key={value}>
              <line x1={pad.left} x2={pad.left + plotW} y1={yOf(value)} y2={yOf(value)} stroke="rgba(15,18,28,0.08)" strokeDasharray="3 5"/>
              <text x={pad.left - 10} y={yOf(value) + 4} textAnchor="end" fontFamily={TOKENS.fontMono} fontSize="10" fill={TOKENS.inkMuted}>{(value * 100).toFixed(0)}</text>
            </g>
          ))}
          {runs.slice(0, -1).map((run, index) => {
            const boundary = runs.slice(0, index + 1).reduce((sum, item) => sum + item.steps.length, 0) - 0.5;
            const x = pad.left + (boundary / maxX) * plotW;
            return (
              <g key={run.id}>
                <line x1={x} x2={x} y1={pad.top} y2={pad.top + plotH} stroke={TOKENS.inkFaint} strokeDasharray="6 6"/>
                <text x={x + 6} y={pad.top + 14} fontFamily={TOKENS.fontText} fontSize="10" fill={TOKENS.inkMuted}>Run {index + 2}</text>
              </g>
            );
          })}
          <path d={lineFor(point => point.best_prob)} fill="none" stroke="oklch(58% 0.14 145)" strokeWidth="3"/>
          <path d={lineFor(point => point.ad_score ?? 0)} fill="none" stroke="oklch(74% 0.13 82)" strokeWidth="3"/>
          {points.map(point => (
            <g key={`${point.runId}-${point.stepIndex}-${point.x}`}>
              <circle
                cx={xOf(point)}
                cy={yOf(point.best_prob)}
                r="6"
                fill={point.best_prob >= 0.5 ? 'oklch(58% 0.14 145)' : 'oklch(58% 0.14 28)'}
                stroke="#fff"
                strokeWidth="2"
                onMouseEnter={() => setHovered(point)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
              />
              <circle
                cx={xOf(point)}
                cy={yOf(point.ad_score ?? 0)}
                r="5"
                fill="oklch(74% 0.13 82)"
                stroke="#fff"
                strokeWidth="2"
                onMouseEnter={() => setHovered(point)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
              />
            </g>
          ))}
          <text x={pad.left} y={height - 14} fontFamily={TOKENS.fontText} fontSize="11" fill={TOKENS.inkMuted}>Molecular state index</text>
          <text x={width - 178} y={height - 14} fontFamily={TOKENS.fontText} fontSize="11" fill="oklch(58% 0.14 145)">P(active)</text>
          <text x={width - 98} y={height - 14} fontFamily={TOKENS.fontText} fontSize="11" fill="oklch(65% 0.13 82)">AD score</text>
        </svg>

        {hovered && (
          <div style={{
            position: 'absolute',
            left: Math.min(780, Math.max(20, (xOf(hovered) / width) * 1000 - 90)),
            top: Math.max(8, yOf(Math.max(hovered.best_prob, hovered.ad_score ?? 0)) - 128),
            width: 188,
            padding: 10,
            borderRadius: 14,
            background: 'rgba(255,255,255,0.92)',
            boxShadow: TOKENS.shadowFloat,
            pointerEvents: 'none',
            zIndex: 5,
          }}>
            <img src={moleculeImageUrl(hovered.best_smiles, 180, 110)} alt={hovered.best_smiles} style={{ width: '100%', height: 92, objectFit: 'contain', background: '#fff', borderRadius: 10 }}/>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontFamily: TOKENS.fontMono, fontSize: 11, color: TOKENS.ink }}>
              <span>P {(hovered.best_prob * 100).toFixed(1)}%</span>
              <span>AD {(hovered.ad_score ?? 0).toFixed(2)}</span>
            </div>
            <div style={{ marginTop: 5, fontFamily: TOKENS.fontText, fontSize: 10.5, color: TOKENS.inkMuted }}>
              Run {hovered.runNumber} - Step {hovered.stepIndex}
            </div>
          </div>
        )}
      </div>
    </Glass>
  );
};

const RealEvolutionPath = ({ runs, onUseAsBase }) => {
  if (!runs.length) return null;

  return (
    <Glass tone="A" radius={26} padding={26} style={{ marginBottom: 22, overflow: 'visible' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 18 }}>
        <div>
          <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>Evolution path archive</div>
          <Caption style={{ marginTop: 3 }}>All retained runs, trimmed at the selected restart point when needed.</Caption>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button type="button" onClick={() => exportDesignRunsCsv(runs)} style={{ appearance: 'none', border: 'none', cursor: 'pointer', padding: '7px 12px', borderRadius: 10, background: 'rgba(255,255,255,0.68)', color: TOKENS.inkSoft, fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 700, boxShadow: TOKENS.shadowInput }}>Export CSV</button>
          <button type="button" onClick={() => exportDesignRunsJson(runs)} style={{ appearance: 'none', border: 'none', cursor: 'pointer', padding: '7px 12px', borderRadius: 10, background: 'rgba(255,255,255,0.68)', color: TOKENS.inkSoft, fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 700, boxShadow: TOKENS.shadowInput }}>Export JSON</button>
          <div style={{
            padding: '5px 10px',
            background: 'rgba(255,255,255,0.7)',
            color: TOKENS.inkMuted,
            borderRadius: 7,
            fontFamily: TOKENS.fontText,
            fontSize: 11,
            fontWeight: 700,
            boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
          }}>
            {runs.length}/7 run{runs.length === 1 ? '' : 's'}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, overflow: 'visible' }}>
        {runs.map((run, runIndex) => (
          <div key={run.id} style={{ padding: 14, borderRadius: 18, background: 'rgba(255,255,255,0.34)', boxShadow: '0 0 0 1px rgba(15,18,28,0.05)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              <div style={{ fontFamily: TOKENS.fontText, fontSize: 13, fontWeight: 800, color: TOKENS.ink }}>Run {runIndex + 1}</div>
              <div style={{ fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkMuted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                start {run.startedFrom} - iter {run.params.iterations} - beam {run.params.beamSize} - top {run.params.topK} - patience {run.params.patience} - {run.params.mmrMode} - AD {run.params.wAd.toFixed(2)} - drug {run.params.druglikeness ? 'on' : 'off'}
              </div>
            </div>
            <div style={{ overflowX: 'auto', paddingBottom: 8 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-start', gap: 0, minWidth: 'max-content' }}>
                {run.steps.map((step, stepIndex) => (
                  <div key={`${run.id}-${step.iteration}-${step.best_smiles}-${stepIndex}`} style={{ display: 'flex', alignItems: 'flex-start' }}>
                    <RealEvolutionStep step={step} index={stepIndex} onUseAsBase={() => onUseAsBase(run.id, stepIndex)}/>
                    {stepIndex < run.steps.length - 1 && (
                      <RealDiffBadge smiA={step.best_smiles} smiB={run.steps[stepIndex + 1].best_smiles}/>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Glass>
  );
};

/* ---------- The page ---------- */
const DesignPage = () => {
  const [smiles, setSmiles] = useState('CCC');
  const [result, setResult] = useState(null);
  const [designRuns, setDesignRuns] = useState([]);
  const [settings, setSettings] = useState({
    nIterations: 5,
    beamSize: 3,
    topK: 3,
    patience: 3,
    useDruglikeness: true,
    mmrMode: 'balanced',
    weights: { wActivity: 0.5, wDiversity: 0.25, wAd: 0.25 },
  });
  const updateSetting = (key, value) => setSettings(current => ({ ...current, [key]: value }));
  const weightsByMode = {
    activity: { wActivity: 0.7, wDiversity: 0.05, wAd: 0.25 },
    balanced: { wActivity: 0.5, wDiversity: 0.25, wAd: 0.25 },
    diversity: { wActivity: 0.1, wDiversity: 0.65, wAd: 0.25 },
  };
  const currentWeights = settings.weights ?? weightsByMode[settings.mmrMode] ?? weightsByMode.balanced;
  const applyPreset = (mode) => {
    setSettings(current => ({
      ...current,
      mmrMode: mode,
      weights: weightsByMode[mode] ?? weightsByMode.balanced,
    }));
  };
  const applyTriangleWeights = (weights) => {
    setSettings(current => ({
      ...current,
      mmrMode: 'custom',
      weights,
    }));
  };
  const runLimitReached = designRuns.length >= 7;
  const runWarning = designRuns.length >= 5 && designRuns.length < 7;
  const mut = useMutation({
    mutationFn: () => {
      if (runLimitReached) throw new Error('Maximum of 7 design runs reached. Start a fresh path to continue.');
      const weights = currentWeights;
      return runDesign(
        smiles.trim(),
        200,
        settings.topK,
        weights.wActivity,
        weights.wDiversity,
        weights.wAd,
        settings.nIterations,
        settings.beamSize,
        100,
        settings.patience,
        settings.useDruglikeness,
      );
    },
    onSuccess: data => {
      const steps = normaliseTimelineSteps(data);
      const run = {
        id: `${Date.now()}-${designRuns.length + 1}`,
        result: data,
        steps,
        startedFrom: data.base_smiles ?? smiles.trim(),
        params: buildRunParams(settings, currentWeights),
      };
      setResult(data);
      setDesignRuns(current => [...current, run].slice(0, 7));
    },
  });
  const candidateCards = useMemo(() => {
    if (!result?.candidates?.length) return [];
    return result.candidates.slice(0, settings.topK).map((candidate, index) => ({
      idx: candidate.rank ?? index + 1,
      delta: ((candidate.delta ?? 0) * 100).toFixed(1),
      pActive: ((candidate.probability ?? 0) * 100).toFixed(1),
      ad: (candidate.ad_score ?? 0).toFixed(2),
      atoms: [candidate.transformation || `iter ${candidate.iteration ?? index + 1}`],
      smiles: candidate.smiles,
    }));
  }, [result, settings.topK]);
  const hasResults = !!result;
  const basePct = hasResults ? (result.base_probability * 100).toFixed(1) : '0.0';
  const bestPct = hasResults ? ((result.top_candidate_prob ?? result.candidates?.[0]?.probability ?? 0) * 100).toFixed(1) : '0.0';
  const deltaPct = hasResults ? (Number(bestPct) - Number(basePct)).toFixed(1) : '0.0';
  const nGenerated = result?.n_generated ?? 0;
  const nValid = result?.n_valid ?? 0;
  const validPct = nGenerated > 0 ? ((nValid / nGenerated) * 100).toFixed(0) : '0';
  const extraRows = Math.max(0, Math.ceil(candidateCards.length / 3) - 1);
  const pageHeight = hasResults ? 1880 + Math.max(0, designRuns.length - 1) * 250 + extraRows * 360 : 980;
  const handleUseAsBase = (runId, stepIndex) => {
    setDesignRuns(current => {
      const runIndex = current.findIndex(run => run.id === runId);
      if (runIndex < 0) return current;
      const next = current.slice(0, runIndex + 1).map((run, index) => (
        index === runIndex ? { ...run, steps: run.steps.slice(0, stepIndex + 1) } : run
      ));
      const selected = next[runIndex].steps[stepIndex];
      if (selected) setSmiles(selected.best_smiles);
      return next;
    });
    setResult(null);
    mut.reset();
  };
  const startFreshPath = () => {
    setDesignRuns([]);
    setResult(null);
    mut.reset();
  };

  return (
  <div style={{ width: 1440, height: 1024, position: 'relative', fontFamily: TOKENS.fontText, color: TOKENS.ink }}>
    <MeshBackground style={{ height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', height: '100%' }}>
        <DesignSidebar/>

        <div data-glass-main style={{ flex: 1, height: '100%', overflowY: 'auto', padding: '8px 20px 20px 4px', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          {/* Top bar */}
          <Glass tone="A" radius={20} padding={0} style={{ marginBottom: 22 }}>
            <DesignTopBar/>
          </Glass>

          {/* Page header */}
          <div style={{ padding: '4px 6px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
              <div>
                <Label style={{ marginBottom: 12, color: TOKENS.accent }}>WORKSPACE - DESIGN</Label>
                <h1 style={{ margin: 0, fontFamily: TOKENS.fontDisplay, fontSize: 56, fontWeight: 700, letterSpacing: '-0.035em', lineHeight: 1, color: TOKENS.ink }}>
                  Molecular Design
                </h1>
                <div style={{ marginTop: 14, fontFamily: TOKENS.fontText, fontSize: 15, color: TOKENS.inkMuted, maxWidth: 620, lineHeight: 1.5 }}>
                  Beam-search optimisation maximising <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.inkSoft }}>P(active)</span> with structural diversity control.
                </div>
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                {designRuns.length > 0 && (
                  <ButtonGhost icon="plus" onClick={startFreshPath}>Fresh path</ButtonGhost>
                )}
              </div>
            </div>
          </div>

          {/* CONFIG PANEL */}
          <Glass tone="A" radius={26} padding={28} style={{ marginBottom: 22, display: 'flex', flexDirection: 'column', gap: 22 }}>

            {/* SMILES input row */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                <Label>Base molecule - SMILES</Label>
                <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="info" size={12}/></span>
              </div>
              <div style={{ display: 'flex', gap: 12, alignItems: 'stretch' }}>
                <div style={{
                  flex: 1, height: 52, display: 'flex', alignItems: 'center', gap: 12,
                  padding: '0 16px',
                  background: 'rgba(255,255,255,0.6)',
                  backdropFilter: 'blur(20px) saturate(160%)',
                  borderRadius: 14,
                  boxShadow: TOKENS.shadowInput,
                }}>
                  <span style={{
                    padding: '3px 8px', borderRadius: 6,
                    background: 'oklch(66% 0.115 155 / 0.14)',
                    color: TOKENS.accentInk,
                    fontFamily: TOKENS.fontText, fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
                  }}>SMILES</span>
                  <input
                    value={smiles}
                    onChange={event => setSmiles(event.target.value)}
                    onKeyDown={event => {
                      if (event.key === 'Enter' && !runLimitReached) mut.mutate();
                    }}
                    style={{
                      flex: 1,
                      border: 'none',
                      outline: 'none',
                      background: 'transparent',
                      fontFamily: TOKENS.fontMono, fontSize: 16, color: TOKENS.ink, fontWeight: 600,
                    }}
                  />
                  <span style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkFaint }}>{result?.base_smiles ?? 'base molecule'}</span>
                </div>
                <button type="button" onClick={() => mut.mutate()} disabled={!smiles.trim() || mut.isPending || runLimitReached} style={{
                  appearance: 'none', border: 'none', cursor: !smiles.trim() || mut.isPending || runLimitReached ? 'not-allowed' : 'pointer',
                  height: 52, padding: '0 24px',
                  display: 'inline-flex', alignItems: 'center', gap: 10,
                  borderRadius: 14,
                  background: `linear-gradient(180deg, oklch(70% 0.13 155), oklch(58% 0.13 155))`,
                  color: '#fff',
                  fontFamily: TOKENS.fontText, fontSize: 14.5, fontWeight: 600, letterSpacing: '-0.005em',
                  boxShadow: '0 1px 0 rgba(255,255,255,0.35) inset, 0 0 0 1px oklch(48% 0.13 155 / 0.5), 0 6px 14px -4px oklch(50% 0.13 155 / 0.45)',
                  opacity: !smiles.trim() || mut.isPending || runLimitReached ? 0.65 : 1,
                }}>
                  {/* Pulsing dot indicating running */}
                  <span style={{ position: 'relative', width: 10, height: 10 }}>
                    <span style={{ position: 'absolute', inset: 0, borderRadius: 999, background: '#fff', opacity: 0.5 }}/>
                    <span style={{ position: 'absolute', inset: 2, borderRadius: 999, background: '#fff' }}/>
                  </span>
                  {mut.isPending ? 'Running design...' : runLimitReached ? 'Run limit reached' : 'Run design'} <span style={{ fontFamily: TOKENS.fontMono, fontWeight: 700, opacity: 0.85 }}>{Math.min(designRuns.length + 1, 7)}/7</span>
                </button>
              </div>
            </div>

            {/* Divider */}
            <div style={{ height: 1, background: TOKENS.glassDivider }}/>

            {/* Generation settings */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 28 }}>
              <div>
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>Generation settings</div>
                  <Caption style={{ marginTop: 3 }}>Beam search, result count, and ranking balance.</Caption>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                  <NumField label="Iterations" value={settings.nIterations} min={2} max={10} hint="Depth of the beam search tree" onChange={value => updateSetting('nIterations', value)}/>
                  <NumField label="Beam size" value={settings.beamSize} min={1} max={20} hint="Candidates kept per iteration" onChange={value => updateSetting('beamSize', value)}/>
                  <NumField label="Top results" value={settings.topK} min={3} max={18} step={3} hint="Final candidates returned" onChange={value => updateSetting('topK', value)}/>
                  <NumField label="Patience" value={settings.patience} min={1} max={6} hint="Stop after N steps without gain" onChange={value => updateSetting('patience', value)}/>
                </div>
                {/* Drug-likeness filter */}
                <div style={{
                  marginTop: 14,
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '14px 16px',
                  background: 'oklch(96% 0.03 155 / 0.55)',
                  borderRadius: 14,
                  boxShadow: '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(66% 0.115 155 / 0.16)',
                }}>
                  <button type="button" onClick={() => updateSetting('useDruglikeness', !settings.useDruglikeness)} style={{ appearance: 'none', border: 'none', background: 'transparent', padding: 0, cursor: 'pointer' }}>
                    <Toggle on={settings.useDruglikeness}/>
                  </button>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: TOKENS.fontText, fontSize: 14, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.005em' }}>Drug-likeness filter</div>
                    <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted, marginTop: 2 }}>Discard candidates that fail Lipinski / QED thresholds.</div>
                  </div>
                  <div style={{
                    padding: '4px 10px',
                    background: 'rgba(255,255,255,0.7)',
                    color: TOKENS.accentInk,
                    borderRadius: 7,
                    fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
                    boxShadow: '0 0 0 1px oklch(66% 0.115 155 / 0.2)',
                  }}>QED &gt;= 0.5</div>
                </div>
              </div>

              {/* MMR weights */}
              <div>
                <MMRWidget
                  mode={settings.mmrMode}
                  weights={currentWeights}
                  onPreset={applyPreset}
                  onWeightsChange={applyTriangleWeights}
                />
              </div>
            </div>
          </Glass>

          {runWarning && (
            <Glass tone="A" radius={16} padding={16} style={{
              marginBottom: 22,
              background: 'oklch(96% 0.04 82 / 0.72)',
              color: 'oklch(42% 0.10 82)',
              fontFamily: TOKENS.fontText,
              fontSize: 13,
              fontWeight: 650,
              boxShadow: '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(74% 0.13 82 / 0.24)',
            }}>
              You have {designRuns.length} retained runs. You can continue up to 7, then start a fresh path for a cleaner optimisation record.
            </Glass>
          )}

          {runLimitReached && (
            <Glass tone="A" radius={16} padding={16} style={{
              marginBottom: 22,
              background: 'oklch(96% 0.04 28 / 0.72)',
              color: 'oklch(42% 0.12 28)',
              fontFamily: TOKENS.fontText,
              fontSize: 13,
              fontWeight: 650,
              boxShadow: '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(70% 0.12 28 / 0.24)',
            }}>
              Maximum path length reached: 7 runs. Start a fresh path before launching another design.
            </Glass>
          )}

          {mut.isError && (
            <Glass tone="A" radius={16} padding={16} style={{
              marginBottom: 22,
              background: 'oklch(96% 0.04 28 / 0.70)',
              color: 'oklch(42% 0.12 28)',
              fontFamily: TOKENS.fontText,
              fontSize: 13,
              fontWeight: 600,
              boxShadow: '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(70% 0.12 28 / 0.24)',
            }}>
              {String(mut.error?.message ?? mut.error)}
            </Glass>
          )}

          {hasResults && (
            <>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 28,
            padding: '14px 22px',
            background: 'linear-gradient(180deg, oklch(96% 0.04 155 / 0.7), oklch(94% 0.04 155 / 0.55))',
            backdropFilter: 'blur(40px) saturate(180%)',
            borderRadius: 18,
            boxShadow: '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(66% 0.115 155 / 0.18), 0 6px 16px -8px oklch(60% 0.13 155 / 0.18)',
            marginBottom: 22,
          }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
              <span style={{ fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: TOKENS.inkMuted }}>Base</span>
              <span style={{ fontFamily: TOKENS.fontMono, fontSize: 18, fontWeight: 700, color: TOKENS.inkSoft }}>{basePct}%</span>
            </div>
            <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={18}/></span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
              <span style={{ fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: TOKENS.inkMuted }}>Best</span>
              <span style={{ fontFamily: TOKENS.fontMono, fontSize: 22, fontWeight: 700, color: TOKENS.accentInk, letterSpacing: '-0.01em' }}>{bestPct}%</span>
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                padding: '2px 8px',
                background: 'oklch(66% 0.115 155 / 0.18)',
                color: TOKENS.accentInk,
                borderRadius: 999,
                fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700,
              }}>{Number(deltaPct) >= 0 ? '+' : ''}{deltaPct}%</span>
            </div>
            <div style={{ flex: 1 }}/>
            <div style={{ display: 'flex', alignItems: 'center', gap: 22 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontFamily: TOKENS.fontMono, fontSize: 16, fontWeight: 700, color: TOKENS.ink }}>{nValid}</span>
                <span style={{ fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted }}>valid</span>
              </div>
              <span style={{ color: TOKENS.inkFaint, fontFamily: TOKENS.fontMono }}>/</span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                <span style={{ fontFamily: TOKENS.fontMono, fontSize: 16, fontWeight: 700, color: TOKENS.ink }}>{nGenerated}</span>
                <span style={{ fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted }}>generated</span>
              </div>
              <div style={{
                padding: '6px 12px',
                background: 'rgba(255,255,255,0.7)',
                borderRadius: 999,
                fontFamily: TOKENS.fontMono, fontSize: 11, color: TOKENS.inkSoft, fontWeight: 600,
                boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
                display: 'inline-flex', alignItems: 'center', gap: 6,
              }}>
                <span style={{ color: TOKENS.accent, display: 'flex' }}><Icon name="check" size={13}/></span>
                {validPct}% valid
              </div>
            </div>
          </div>

          {candidateCards.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18, marginBottom: 22 }}>
              {candidateCards.map(card => (
                <CandidateCard key={`${card.idx}-${card.smiles ?? card.pActive}`} {...card}/>
              ))}
            </div>
          )}

            </>
          )}

          {designRuns.length > 0 && (
            <>
              <DesignPathPlot runs={designRuns}/>
              <RealEvolutionPath runs={designRuns} onUseAsBase={handleUseAsBase}/>
            </>
          )}
        </div>
      </div>
    </MeshBackground>
  </div>
  );
};

export default DesignPage;




