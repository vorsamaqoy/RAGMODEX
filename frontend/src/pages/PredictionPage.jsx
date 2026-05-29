import { useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { TOKENS, MeshBackground, Glass, Label, Caption, Icon, Tab, ButtonGhost } from '../glass';
import { moleculeImageUrl, predict } from '../lib/api';
import { GlassLlmModelSelect } from '../components/GlassLlmModelSelect';
import { GlassSettingsShortcut } from '../components/GlassSettingsShortcut';

/* RAGMODEX Glass - Bioactivity Prediction page */

const PredSidebar = () => {
  const items = [
    { i: 'chat', l: 'Chat' },
    { i: 'flask', l: 'Prediction', active: true },
    { i: 'layers', l: 'Design' },
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
          padding: '9px 12px', borderRadius: 12,
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

const PredTopBar = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 24px 14px 12px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: TOKENS.fontText, fontSize: 13.5, color: TOKENS.inkMuted }}>
      <span>RAGMODEX</span>
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={14}/></span>
      <span style={{ color: TOKENS.ink, fontWeight: 600 }}>Bioactivity Prediction</span>
    </div>
    <Glass tone="B" radius={14} padding={4} style={{ display: 'flex', gap: 2 }}>
      <Tab icon="cpu" label="Model" active dot/>
      <Tab icon="db" label="Dataset" dot/>
      <GlassLlmModelSelect/>
    </Glass>
  </div>
);

/* ---------- SHAP bar chart ---------- */
const DEFAULT_SHAP_DATA = [
  { bit: 'bit 1873', value: 0.0312 },
  { bit: 'bit 1750', value: 0.0180 },
  { bit: 'bit 1535', value: -0.0134 },
  { bit: 'bit 1220', value: -0.0099 },
  { bit: 'bit 361',  value: -0.0076 },
  { bit: 'bit 1016', value: -0.0075 },
  { bit: 'bit 1946', value: -0.0071 },
  { bit: 'bit 935',  value: -0.0058 },
  { bit: 'bit 43',   value: -0.0054 },
  { bit: 'bit 1738', value: -0.0053 },
];

const SHAPChart = ({ data = DEFAULT_SHAP_DATA }) => {
  const maxAbs = 0.034;
  const rowH = 30;
  const rows = data.length;
  const totalH = rows * rowH + 36;
  const chartW = 540;
  const labelW = 70;
  const innerW = chartW - labelW - 60; // padding right
  const midX = labelW + innerW / 2;

  return (
    <svg viewBox={`0 0 ${chartW} ${totalH}`} width="100%" height={totalH} style={{ display: 'block' }}>
      {/* Grid lines */}
      {[-1, -0.5, 0, 0.5, 1].map((t, i) => {
        const x = midX + (t * innerW / 2);
        return (
          <line key={i} x1={x} y1={6} x2={x} y2={rows * rowH + 6}
            stroke={t === 0 ? 'rgba(15,18,28,0.18)' : 'rgba(15,18,28,0.06)'}
            strokeWidth={t === 0 ? 1 : 0.8}
            strokeDasharray={t === 0 ? '0' : '3 3'}/>
        );
      })}
      {/* Bars */}
      {data.map((d, i) => {
        const y = 6 + i * rowH + 6;
        const w = Math.abs(d.value) / maxAbs * (innerW / 2);
        const isPos = d.value > 0;
        const x = isPos ? midX : midX - w;
        const fill = isPos ? 'oklch(66% 0.115 155)' : 'oklch(60% 0.165 25)';
        const fillSoft = isPos ? 'oklch(74% 0.13 155)' : 'oklch(70% 0.16 25)';
        return (
          <g key={i}>
            <text x={labelW - 8} y={y + 13} textAnchor="end" fontSize="11" fontFamily={TOKENS.fontMono} fill={TOKENS.inkMuted}>{d.bit}</text>
            <defs>
              <linearGradient id={`g${i}`} x1="0" x2={isPos ? '1' : '-1'} y1="0" y2="0">
                <stop offset="0%" stopColor={fillSoft}/>
                <stop offset="100%" stopColor={fill}/>
              </linearGradient>
            </defs>
            <rect x={x} y={y} width={w} height={18} rx="4" fill={`url(#g${i})`}/>
            <text
              x={isPos ? x + w + 6 : x - 6}
              y={y + 13}
              textAnchor={isPos ? 'start' : 'end'}
              fontSize="10.5" fontFamily={TOKENS.fontMono} fontWeight="600"
              fill={isPos ? 'oklch(40% 0.1 155)' : 'oklch(45% 0.16 25)'}>
              {d.value > 0 ? '+' : ''}{d.value.toFixed(4)}
            </text>
          </g>
        );
      })}
      {/* X-axis labels */}
      {[-0.031, -0.016, 0, 0.016, 0.031].map((t, i) => {
        const x = midX + (t / maxAbs) * (innerW / 2);
        return (
          <text key={i} x={x} y={rows * rowH + 24} textAnchor="middle" fontSize="9.5" fontFamily={TOKENS.fontMono} fill={TOKENS.inkFaint}>
            {t > 0 ? '+' : ''}{t.toFixed(3)}
          </text>
        );
      })}
    </svg>
  );
};

/* ---------- Molecule placeholder ---------- */
const PlaceholderMolecule = ({ smiles }) => (
  smiles ? (
    <img src={moleculeImageUrl(smiles, 520, 300)} alt={`Molecule ${smiles}`} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}/>
  ) : (
    <svg viewBox="0 0 240 140" width="100%" height="100%">
      <path d="M40 95 L80 55 L120 95 L160 55 L200 95" stroke="#0e1014" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
);

/* ---------- Bit pill ---------- */
const BitPill = ({ id, tone = 'active', selected, onClick }) => {
  const styles = {
    active:   { bg: 'oklch(66% 0.115 155 / 0.18)', color: 'oklch(38% 0.085 155)', ring: 'oklch(66% 0.115 155 / 0.4)' },
    mixed:    { bg: 'oklch(78% 0.13 65 / 0.22)',   color: 'oklch(45% 0.13 65)',  ring: 'oklch(70% 0.13 65 / 0.45)' },
    inactive: { bg: 'oklch(70% 0.16 25 / 0.18)',   color: 'oklch(45% 0.16 25)',  ring: 'oklch(70% 0.16 25 / 0.4)' },
  }[tone];
  return (
    <button type="button" onClick={onClick} style={{
      appearance: 'none',
      border: 'none',
      cursor: 'pointer',
      padding: '6px 14px',
      borderRadius: 999,
      background: styles.bg,
      color: styles.color,
      fontFamily: TOKENS.fontMono, fontSize: 13, fontWeight: 700,
      boxShadow: selected
        ? `0 0 0 2px ${styles.ring}, 0 6px 16px -8px rgba(15,18,28,0.25), 0 1px 0 rgba(255,255,255,0.7) inset`
        : `0 0 0 1px ${styles.ring}, 0 1px 0 rgba(255,255,255,0.7) inset`,
    }}>{id}</button>
  );
};

/* ---------- Mini metric row ---------- */
const FpRow = ({ label, value }) => (
  <div style={{
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '9px 12px',
    background: 'rgba(255,255,255,0.5)',
    borderRadius: 9,
    boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
  }}>
    <span style={{ fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, fontWeight: 500 }}>{label}</span>
    <span style={{ fontFamily: TOKENS.fontMono, fontSize: 13, color: TOKENS.ink, fontWeight: 700 }}>{value}</span>
  </div>
);

/* ---------- The page ---------- */
const PredictionPage = () => {
  const [smiles, setSmiles] = useState('');
  const [result, setResult] = useState(null);
  const [selectedBitId, setSelectedBitId] = useState(null);
  const mut = useMutation({
    mutationFn: () => predict(smiles),
    onSuccess: data => {
      setResult(data);
      const firstBit = data.active_bits?.[0] ?? data.top_bits?.[0];
      setSelectedBitId(firstBit ? String(firstBit.bit_index ?? firstBit.bit) : null);
    },
  });

  const activeProbability = result ? result.probability_active : 0.0767;
  const activePct = activeProbability * 100;
  const prediction = result?.prediction ?? 'Inactive';
  const isPredictionActive = prediction === 'Active';
  const canonical = result?.canonical_smiles ?? smiles;
  const shapData = useMemo(() => {
    if (!result?.top_bits?.length) return DEFAULT_SHAP_DATA;
    return result.top_bits.slice(0, 10).map(bit => ({
      bit: bit.bit.replace(/^ECFP\d+_/, 'bit '),
      value: bit.shap_value,
    }));
  }, [result]);
  const tableRows = result?.top_bits?.slice(0, 6).map((bit, index) => ({
    i: index + 1,
    bit: bit.bit,
    shap: `${bit.shap_value > 0 ? '+' : ''}${bit.shap_value.toFixed(5)}`,
    dir: bit.shap_value > 0 ? 'Active' : 'Inactive',
    sub: bit.molecule_substructures?.[0]?.smiles ?? (bit.bit_on ? 'bit ON' : 'bit OFF'),
    state: bit.bit_on ? 'bit ON' : 'bit OFF',
  })) ?? [
    { i: 1, bit: 'ECFP6_1873', shap: '+0.03120', dir: 'Active',   sub: 'c1ccc(C)cc1',     state: 'bit OFF' },
    { i: 2, bit: 'ECFP6_1750', shap: '+0.01804', dir: 'Active',   sub: 'Cc1ccccc1N',      state: 'bit OFF' },
    { i: 3, bit: 'ECFP6_1535', shap: '-0.01340', dir: 'Inactive', sub: 'CCCC',            state: 'bit ON' },
    { i: 4, bit: 'ECFP6_1220', shap: '-0.00993', dir: 'Inactive', sub: 'CCC(C)C',         state: 'bit ON' },
    { i: 5, bit: 'ECFP6_361',  shap: '-0.00760', dir: 'Inactive', sub: 'CC(C)CC',         state: 'bit ON' },
    { i: 6, bit: 'ECFP6_1016', shap: '-0.00750', dir: 'Inactive', sub: 'CC(C)C',          state: 'bit ON' },
  ];
  const collisionBits = useMemo(() => {
    if (!result) return [];
    const source = result.active_bits?.length ? result.active_bits : result.top_bits ?? [];
    return source.map(bit => {
      const id = String(bit.bit_index ?? bit.bit);
      const trainingInfo = bit.training_info;
      const ratio = trainingInfo?.active_ratio;
      const tone = trainingInfo?.is_ambiguous ? 'mixed' : ratio != null && ratio < 0.5 ? 'inactive' : 'active';
      const trainingSubs = Object.entries(trainingInfo?.substructures ?? {}).map(([smilesValue, count]) => ({
        smiles: smilesValue,
        count,
        radius: trainingInfo?.radii?.[smilesValue]?.[0] ?? null,
        source: 'training',
      }));
      const moleculeSubs = (bit.molecule_substructures ?? []).map(sub => ({
        smiles: sub.smiles,
        count: null,
        radius: sub.radius,
        source: 'query',
      }));
      const seen = new Set();
      const substructures = [...moleculeSubs, ...trainingSubs].filter(sub => {
        if (!sub.smiles || seen.has(sub.smiles)) return false;
        seen.add(sub.smiles);
        return true;
      });
      return {
        id,
        label: bit.bit?.replace(/^ECFP\d+_/, '') ?? id,
        bit,
        tone,
        trainingInfo,
        substructures,
      };
    }).slice(0, 12);
  }, [result]);
  const selectedBit = collisionBits.find(bit => bit.id === selectedBitId) ?? collisionBits[0] ?? null;
  const maxSubCount = Math.max(1, ...(selectedBit?.substructures ?? []).map(sub => Number(sub.count ?? 1)));
  const exportCsv = () => {
    const csv = [
      'rank,bit,shap,direction,substructure,state',
      ...tableRows.map(row => [row.i, row.bit, row.shap, row.dir, `"${String(row.sub).replaceAll('"', '""')}"`, row.state].join(',')),
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ragmodex-prediction-bits.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
  <div style={{ width: 1440, height: 1024, position: 'relative', fontFamily: TOKENS.fontText, color: TOKENS.ink }}>
    <MeshBackground style={{ height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', height: '100%' }}>
        <PredSidebar/>

        <div data-glass-main style={{ flex: 1, height: '100%', overflowY: 'auto', padding: '8px 20px 20px 4px', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          {/* Top bar */}
          <Glass tone="A" radius={20} padding={0} style={{ marginBottom: 22 }}>
            <PredTopBar/>
          </Glass>

          {/* Hero */}
          <div style={{ padding: '4px 6px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
              <div>
                <Label style={{ marginBottom: 12, color: TOKENS.accent }}>WORKSPACE - PREDICTION</Label>
                <h1 style={{ margin: 0, fontFamily: TOKENS.fontDisplay, fontSize: 56, fontWeight: 700, letterSpacing: '-0.035em', lineHeight: 1, color: TOKENS.ink }}>
                  Bioactivity Prediction
                </h1>
                <div style={{ marginTop: 14, fontFamily: TOKENS.fontText, fontSize: 15, color: TOKENS.inkMuted, maxWidth: 620, lineHeight: 1.5 }}>
                  Configurable <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.inkSoft }}>ECFP</span> fingerprint - SHAP feature importance per single molecule.
                </div>
              </div>
            </div>
          </div>

          {/* SMILES input row */}
          <Glass tone="A" radius={22} padding={16} style={{ marginBottom: 22 }}>
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
                    if (event.key === 'Enter' && smiles.trim() && !mut.isPending) mut.mutate();
                  }}
                  aria-label="SMILES"
                  style={{
                    flex: 1,
                    appearance: 'none',
                    border: 'none',
                    outline: 'none',
                    background: 'transparent',
                    fontFamily: TOKENS.fontMono,
                    fontSize: 16,
                    color: TOKENS.ink,
                    fontWeight: 600,
                  }}
                />
                <span style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkFaint }}>{canonical}</span>
              </div>
              <button type="button" onClick={() => smiles.trim() && mut.mutate()} disabled={!smiles.trim() || mut.isPending} style={{
                appearance: 'none', border: 'none', cursor: !smiles.trim() || mut.isPending ? 'not-allowed' : 'pointer',
                height: 52, padding: '0 30px',
                display: 'inline-flex', alignItems: 'center', gap: 10,
                borderRadius: 14,
                background: mut.isPending ? 'rgba(15,18,28,0.18)' : `linear-gradient(180deg, oklch(70% 0.13 155), oklch(58% 0.13 155))`,
                color: '#fff',
                fontFamily: TOKENS.fontText, fontSize: 14.5, fontWeight: 600, letterSpacing: '-0.005em',
                boxShadow: '0 1px 0 rgba(255,255,255,0.35) inset, 0 0 0 1px oklch(48% 0.13 155 / 0.5), 0 6px 14px -4px oklch(50% 0.13 155 / 0.45)',
              }}>
                <Icon name="sparkle" size={16}/>
                {mut.isPending ? 'Predicting...' : 'Predict'}
              </button>
            </div>
            {mut.error && (
              <div style={{ marginTop: 10, fontFamily: TOKENS.fontText, fontSize: 12.5, color: 'oklch(45% 0.16 25)', fontWeight: 600 }}>
                {String(mut.error.message ?? mut.error)}
              </div>
            )}
          </Glass>

          {result && (
          <>
          {/* Two columns: molecule + SHAP */}
          <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 18, marginBottom: 22 }}>
            {/* LEFT */}
            <Glass tone="A" radius={22} padding={18} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Molecule */}
              <div style={{
                background: 'linear-gradient(180deg, rgba(255,255,255,0.85), rgba(255,255,255,0.55))',
                borderRadius: 16,
                boxShadow: '0 1px 0 rgba(255,255,255,0.95) inset, 0 0 0 1px rgba(15,18,28,0.05)',
                aspectRatio: '240/140',
                padding: 10,
              }}>
                <PlaceholderMolecule smiles={canonical}/>
              </div>

              {/* Verdict pill */}
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  padding: '7px 16px',
                  background: isPredictionActive ? 'oklch(66% 0.115 155 / 0.14)' : 'oklch(70% 0.16 25 / 0.14)',
                  color: isPredictionActive ? TOKENS.accentInk : 'oklch(45% 0.16 25)',
                  borderRadius: 999,
                  fontFamily: TOKENS.fontText, fontSize: 13.5, fontWeight: 700, letterSpacing: '-0.005em',
                  boxShadow: '0 0 0 1px oklch(70% 0.16 25 / 0.3)',
                }}>
                  <span style={{ width: 7, height: 7, borderRadius: 999, background: isPredictionActive ? TOKENS.accent : 'oklch(60% 0.16 25)' }}/>
                  {prediction}
                </div>
              </div>

              {/* P(active) bar */}
              <div>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, fontWeight: 500 }}>P(active)</div>
                  <div style={{ fontFamily: TOKENS.fontMono, fontSize: 24, fontWeight: 700, color: 'oklch(45% 0.16 25)', letterSpacing: '-0.02em' }}>
                    {activePct.toFixed(2)}<span style={{ fontSize: 14, color: TOKENS.inkMuted, fontWeight: 500 }}>%</span>
                  </div>
                </div>
                <div style={{ position: 'relative', height: 8, background: 'rgba(15,18,28,0.06)', borderRadius: 999, overflow: 'hidden' }}>
                  <div style={{
                    position: 'absolute', inset: 0, width: `${Math.max(0, Math.min(100, activePct))}%`,
                    background: isPredictionActive ? `linear-gradient(90deg, oklch(72% 0.13 155), oklch(58% 0.13 155))` : `linear-gradient(90deg, oklch(70% 0.16 25), oklch(60% 0.16 25))`,
                    borderRadius: 999,
                  }}/>
                  {/* 50% mark */}
                  <div style={{ position: 'absolute', left: '50%', top: -2, bottom: -2, width: 1, background: 'rgba(15,18,28,0.18)' }}/>
                </div>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  marginTop: 8, fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkFaint,
                }}>
                  <span>0%</span>
                  <span>50% - threshold</span>
                  <span>100%</span>
                </div>
              </div>

              {/* Fingerprint details */}
              <div>
                <Label style={{ marginBottom: 10 }}>Fingerprint details</Label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <FpRow label="Bits ON" value={result?.n_on_bits ?? 9}/>
                  <FpRow label="Total bits" value={(result?.n_bits ?? 2048).toLocaleString()}/>
                  <FpRow label="FP radius" value={result?.radius ?? 3}/>
                  <FpRow label="Baseline P(active)" value={result ? result.expected_value.toFixed(4) : '0.4958'}/>
                </div>
              </div>
            </Glass>

            {/* RIGHT: SHAP */}
            <Glass tone="A" radius={22} padding={22}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
                <div>
                  <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>SHAP Feature Importance</div>
                  <Caption style={{ marginTop: 3 }}>Top 10 most influential fingerprint bits for this molecule.</Caption>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <div style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    padding: '5px 10px',
                    background: 'oklch(66% 0.115 155 / 0.16)',
                    color: TOKENS.accentInk,
                    borderRadius: 7,
                    fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700,
                  }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: 'oklch(66% 0.115 155)' }}/>
                    pushes active
                  </div>
                  <div style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    padding: '5px 10px',
                    background: 'oklch(70% 0.16 25 / 0.16)',
                    color: 'oklch(45% 0.16 25)',
                    borderRadius: 7,
                    fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700,
                  }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: 'oklch(60% 0.16 25)' }}/>
                    pushes inactive
                  </div>
                </div>
              </div>

              <SHAPChart data={shapData}/>

              <div style={{ marginTop: 6, textAlign: 'center', fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkFaint }}>
                SHAP value - contribution to log-odds of active class
              </div>
            </Glass>
          </div>

          {/* Bit Collision Map */}
          <Glass tone="A" radius={22} padding={22} style={{ marginBottom: 22 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 18 }}>
              <div>
                <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>Bit Collision Map</div>
                <Caption style={{ marginTop: 3 }}>{collisionBits.length} active bits - select one to inspect its substructures.</Caption>
              </div>
              {/* Gradient legend */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontFamily: TOKENS.fontText, fontSize: 11, color: TOKENS.inkMuted, fontWeight: 500 }}>mixed</span>
                <div style={{
                  width: 120, height: 8, borderRadius: 999,
                  background: 'linear-gradient(90deg, oklch(70% 0.16 25), oklch(78% 0.13 65), oklch(66% 0.115 155))',
                  boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
                }}/>
                <span style={{ fontFamily: TOKENS.fontText, fontSize: 11, color: TOKENS.inkMuted, fontWeight: 500 }}>dominant</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
              {/* Left: bit pills */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <Label>Active bits</Label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {collisionBits.map(bit => (
                    <BitPill
                      key={bit.id}
                      id={bit.label}
                      tone={bit.tone}
                      selected={selectedBit?.id === bit.id}
                      onClick={() => setSelectedBitId(bit.id)}
                    />
                  ))}
                </div>
                <div style={{
                  marginTop: 8,
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 12px',
                  background: 'rgba(255,255,255,0.5)',
                  borderRadius: 10,
                  boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
                }}>
                  <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="info" size={14}/></span>
                  <span style={{ fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted, lineHeight: 1.45 }}>
                    Click a bit to see its substructure(s) and their relative coverage in the active set.
                  </span>
                </div>
              </div>

              {/* Right: collision detail */}
              <div style={{
                padding: 16,
                background: 'rgba(255,255,255,0.55)',
                borderRadius: 16,
                boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.06)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <div style={{ fontFamily: TOKENS.fontText, fontSize: 13.5, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.005em' }}>
                    Bit <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.accentInk }}>{selectedBit?.label ?? '-'}</span>
                  </div>
                  <span style={{
                    padding: '3px 9px', borderRadius: 6,
                    background: 'oklch(78% 0.13 65 / 0.2)',
                    color: 'oklch(45% 0.13 65)',
                    fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
                  }}>{selectedBit?.trainingInfo?.is_ambiguous ? 'collision' : 'selected'}</span>
                </div>
                <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted, marginBottom: 12 }}>
                  {(selectedBit?.substructures.length ?? 0).toLocaleString()} substructures cited for this bit
                  {selectedBit?.trainingInfo?.dominant_substructure ? ` · dominant: ${selectedBit.trainingInfo.dominant_substructure}` : ''}
                </div>

                {/* Substructure rows */}
                {(selectedBit?.substructures ?? []).slice(0, 5).map((s, i) => {
                  const cov = (Number(s.count ?? 1) / maxSubCount) * 100;
                  return (
                  <div key={i} style={{
                    display: 'grid', gridTemplateColumns: '1fr 50px', alignItems: 'center', gap: 12,
                    padding: '8px 4px',
                  }}>
                    <div style={{ position: 'relative' }}>
                      <div style={{ position: 'absolute', inset: 0, background: 'rgba(15,18,28,0.06)', borderRadius: 6 }}/>
                      <div style={{
                        position: 'absolute', top: 0, bottom: 0, left: 0,
                        width: `${cov}%`,
                        background: selectedBit?.tone === 'inactive' ? 'oklch(70% 0.16 25 / 0.22)' : 'oklch(66% 0.115 155 / 0.25)',
                        borderRadius: 6,
                      }}/>
                      <div style={{
                        position: 'relative', padding: '6px 10px',
                        fontFamily: TOKENS.fontMono, fontSize: 11.5, color: TOKENS.inkSoft, fontWeight: 600,
                      }}>{s.smiles}</div>
                    </div>
                    <div style={{ fontFamily: TOKENS.fontMono, fontSize: 12, color: TOKENS.ink, fontWeight: 700, textAlign: 'right' }}>{s.count ?? 'query'}</div>
                  </div>
                )})}
              </div>
            </div>
          </Glass>

          {/* Bit Details */}
          <Glass tone="A" radius={22} padding={22}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
              <div>
                <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>Bit Details</div>
                <Caption style={{ marginTop: 3 }}>
                  Substructures cited by the selected collision-map bit, rendered through the RDKit molecule endpoint.
                </Caption>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <ButtonGhost icon="upload" onClick={exportCsv}>Export CSV</ButtonGhost>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
              {(selectedBit?.substructures ?? []).map((sub, idx) => (
                <div key={`${sub.smiles}-${idx}`} style={{
                  background: 'rgba(255,255,255,0.55)',
                  borderRadius: 16,
                  boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.06)',
                  overflow: 'hidden',
                }}>
                  <div style={{ height: 150, background: '#fff', padding: 10 }}>
                    <img
                      src={moleculeImageUrl(sub.smiles, 260, 150)}
                      alt={sub.smiles}
                      style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
                      loading="lazy"
                      decoding="async"
                    />
                  </div>
                  <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div style={{
                      fontFamily: TOKENS.fontMono,
                      fontSize: 11.5,
                      color: TOKENS.inkSoft,
                      fontWeight: 600,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>{sub.smiles}</div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted }}>
                      <span>{sub.source}</span>
                      <span>{sub.count == null ? 'query fragment' : `${sub.count} hits`}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Glass>
          </>
          )}
        </div>
      </div>
    </MeshBackground>
  </div>
  );
};

export default PredictionPage;






