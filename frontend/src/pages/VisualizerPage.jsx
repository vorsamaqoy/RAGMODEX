import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TOKENS, MeshBackground, Glass, Label, Caption, Icon, Tab, MetricTile } from '../glass';
import { getVisualizerData, moleculeImageUrl } from '../lib/api';
import { GlassLlmModelSelect } from '../components/GlassLlmModelSelect';
import { GlassSettingsShortcut } from '../components/GlassSettingsShortcut';

/* RAGMODEX Glass - Molecule Visualizer */

const VizSidebar = () => {
  const items = [
    { i: 'chat', l: 'Chat' },
    { i: 'flask', l: 'Prediction' },
    { i: 'layers', l: 'Design' },
    { i: 'search', l: 'Screening' },
    { i: 'chart', l: 'Evaluation' },
    { i: 'sparkle', l: 'Visualizer', active: true },
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

const VizTopBar = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 24px 14px 12px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: TOKENS.fontText, fontSize: 13.5, color: TOKENS.inkMuted }}>
      <span>RAGMODEX</span>
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={14}/></span>
      <span style={{ color: TOKENS.ink, fontWeight: 600 }}>Visualizer</span>
    </div>
    <Glass tone="B" radius={14} padding={4} style={{ display: 'flex', gap: 2 }}>
      <Tab icon="cpu" label="Model" active dot/>
      <Tab icon="db" label="Dataset" dot/>
      <GlassLlmModelSelect/>
    </Glass>
  </div>
);

/* ---------- Distribution histogram ---------- */
const DistChart = () => {
  // 50 buckets across [0,1]; bimodal-ish but very skewed: huge inactive cluster near 0, tiny active cluster near 1
  const buckets = [];
  for (let i = 0; i < 50; i++) {
    const p = i / 49;
    let inactive = 0, active = 0;
    if (p < 0.05) inactive = 620;
    else if (p < 0.10) inactive = 180;
    else if (p < 0.15) inactive = 65;
    else if (p < 0.20) inactive = 30;
    else if (p < 0.30) inactive = 12;
    else if (p < 0.45) inactive = 4;
    else if (p < 0.50) inactive = 1;
    if (p > 0.92) active = 38;
    else if (p > 0.85) active = 28;
    else if (p > 0.75) active = 14;
    else if (p > 0.65) active = 8;
    else if (p > 0.55) active = 4;
    else if (p > 0.50) active = 2;
    buckets.push({ p, inactive, active });
  }
  const maxV = 650;
  const W = 1100, H = 280;
  const padL = 50, padR = 12, padT = 16, padB = 44;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const bw = innerW / buckets.length;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block' }}>
      {/* Y grid */}
      {[0, 200, 400, 600].map((v, i) => (
        <g key={i}>
          <line x1={padL} y1={padT + innerH - (v / maxV) * innerH} x2={padL + innerW} y2={padT + innerH - (v / maxV) * innerH} stroke="rgba(15,18,28,0.06)" strokeWidth="0.8" strokeDasharray="3 3"/>
          <text x={padL - 8} y={padT + innerH - (v / maxV) * innerH + 3} textAnchor="end" fontSize="10" fontFamily={TOKENS.fontMono} fill={TOKENS.inkFaint}>{v}</text>
        </g>
      ))}
      {/* Axis lines */}
      <line x1={padL} y1={padT + innerH} x2={padL + innerW} y2={padT + innerH} stroke="rgba(15,18,28,0.25)" strokeWidth="1"/>
      <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} stroke="rgba(15,18,28,0.25)" strokeWidth="1"/>
      {/* Threshold line at p=0.5 */}
      <line x1={padL + innerW * 0.5} y1={padT} x2={padL + innerW * 0.5} y2={padT + innerH} stroke="oklch(60% 0.16 50)" strokeWidth="1.4" strokeDasharray="5 5"/>
      <text x={padL + innerW * 0.5 + 6} y={padT + 10} fontSize="10" fontFamily={TOKENS.fontMono} fill="oklch(50% 0.16 50)" fontWeight="600">threshold 0.50</text>
      {/* Bars */}
      {buckets.map((b, i) => {
        const x = padL + i * bw;
        const iH = (b.inactive / maxV) * innerH;
        const aH = (b.active / maxV) * innerH;
        return (
          <g key={i}>
            {b.inactive > 0 && (
              <rect x={x + 0.4} y={padT + innerH - iH} width={bw - 0.8} height={iH} fill="oklch(62% 0.16 25)" rx="1"/>
            )}
            {b.active > 0 && (
              <rect x={x + 0.4} y={padT + innerH - aH} width={bw - 0.8} height={aH} fill="oklch(60% 0.13 155)" rx="1"/>
            )}
          </g>
        );
      })}
      {/* X labels */}
      {[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1].map((t, i) => (
        <text key={i} x={padL + t * innerW} y={padT + innerH + 16} textAnchor="middle" fontSize="10" fontFamily={TOKENS.fontMono} fill={TOKENS.inkFaint}>{t.toFixed(1)}</text>
      ))}
      <text x={padL + innerW / 2} y={H - 6} textAnchor="middle" fontSize="11" fontFamily={TOKENS.fontText} fill={TOKENS.inkMuted} fontWeight="600">P(active)</text>
      <text x={14} y={padT + innerH / 2} textAnchor="middle" fontSize="11" fontFamily={TOKENS.fontText} fill={TOKENS.inkMuted} fontWeight="600" transform={`rotate(-90 14 ${padT + innerH / 2})`}>Count</text>
    </svg>
  );
};

/* ---------- Molecule placeholder (variants) ---------- */
const MolMini = ({ seed = 0 }) => {
  // Different schematic skeletons; consistent atom palette
  const variants = [
    // ring + chain + OH
    'M40 80 Q50 60 60 80 Q70 100 80 80 Q90 60 100 80 L130 95 L160 80',
    // double ring zig zag
    'M40 80 L60 60 L80 80 L100 60 L120 80 L140 60 L160 80',
    // ester
    'M40 60 L70 80 L100 60 L130 80 L160 60',
    // amine branched
    'M40 90 L60 70 L80 90 L100 70 L120 90 L100 110',
    // aromatic chain
    'M40 80 L65 65 L65 95 L40 110 M65 65 L90 80 L90 110 L65 95 M90 80 L120 70 L150 80',
    // simple line + dot
    'M40 85 L70 65 L100 85 L130 65 L160 85',
  ];
  const path = variants[seed % variants.length];
  const atoms = [
    [['OH', 38, 78, 'oklch(55% 0.18 30)']],
    [['Cl', 42, 60, 'oklch(50% 0.16 155)'], ['HO', 168, 80, 'oklch(55% 0.18 30)']],
    [['O', 38, 60, 'oklch(55% 0.16 50)'], ['HO', 168, 60, 'oklch(55% 0.18 30)']],
    [['HN', 36, 90, 'oklch(50% 0.15 250)'], ['Cl', 100, 110, 'oklch(50% 0.16 155)']],
    [['HBr', 162, 80, 'oklch(50% 0.16 30)']],
    [['F', 38, 85, 'oklch(60% 0.13 220)']],
  ][seed % 6];
  return (
    <svg viewBox="0 0 200 130" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
      <path d={path} stroke="#0e1014" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      {atoms.map(([lbl, x, y, c], i) => (
        <g key={i}>
          <rect x={x - 12} y={y - 10} width={lbl.length > 1 ? 24 : 14} height="18" rx="3" fill="#fff"/>
          <text x={x + (lbl.length > 1 ? 0 : 0)} y={y + 4} textAnchor="middle" fontSize="11" fontWeight="700" fontFamily={TOKENS.fontDisplay} fill={c}>{lbl}</text>
        </g>
      ))}
    </svg>
  );
};

/* ---------- Molecule card ---------- */
const MoleculeCard = ({ idx, smiles, p, active }) => (
  <div style={{
    background: 'rgba(255,255,255,0.55)',
    backdropFilter: 'blur(40px) saturate(180%)',
    borderRadius: 18,
    boxShadow: TOKENS.shadowCard,
    overflow: 'hidden',
    display: 'flex', flexDirection: 'column',
  }}>
    {/* Structure */}
    <div style={{
      background: 'linear-gradient(180deg, #fff, rgba(255,255,255,0.7))',
      aspectRatio: '4/3',
      borderBottom: '1px solid rgba(15,18,28,0.05)',
      padding: 8,
    }}>
      {smiles ? (
        <img
          src={moleculeImageUrl(smiles, 240, 170)}
          alt={smiles}
          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
          loading="lazy"
          decoding="async"
        />
      ) : (
        <MolMini seed={idx}/>
      )}
    </div>
    {/* Footer */}
    <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{
          fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkFaint, fontWeight: 600,
        }}>#{idx}</span>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: '2px 8px',
          background: active ? 'oklch(66% 0.115 155 / 0.16)' : 'oklch(70% 0.16 25 / 0.16)',
          color: active ? TOKENS.accentInk : 'oklch(45% 0.16 25)',
          borderRadius: 999,
          fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 700,
        }}>
          <span style={{ width: 5, height: 5, borderRadius: 999, background: active ? 'oklch(60% 0.13 155)' : 'oklch(60% 0.16 25)' }}/>
          {active ? 'Active' : 'Inactive'}
        </span>
        <div style={{ flex: 1 }}/>
        <span style={{ fontFamily: TOKENS.fontMono, fontSize: 11.5, color: TOKENS.ink, fontWeight: 700 }}>
          P = {p}
        </span>
      </div>
      <div style={{
        fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkMuted, fontWeight: 500,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>{smiles}</div>
    </div>
  </div>
);

/* ---------- The page ---------- */
const VisualizerPage = () => {
  const [page, setPage] = useState(1);
  const [filterClass, setFilterClass] = useState('all');
  const [sort, setSort] = useState('default');
  const [search, setSearch] = useState('');
  const q = useQuery({
    queryKey: ['visualizer', page, filterClass, sort, search],
    queryFn: () => getVisualizerData(page, 48, filterClass, sort, search),
    retry: false,
  });
  const staticRows = [
    { i: 0,  s: 'CCC(CC)CN1C(=O)S/C(=C\\c2ccc(O)c(C(F)F)c2)C1=', p: '0.035', a: false },
    { i: 1,  s: 'CC(CN1C(=O)S/C(=C\\c2ccc(O)c(C(F)F)c2)C1=', p: '0.016', a: false },
    { i: 2,  s: 'O=C(Oc1ccc(F)c1OC(=O)c1ccccc1Oc1ccccc1)', p: '0.016', a: false },
    { i: 3,  s: 'O=C(CCc1ccc(O)cc1)c1c(O)cc(O)cc1O', p: '0.011', a: false },
    { i: 4,  s: 'CCN(CC)CCn1c(=N)n(CC(O)c2ccc(Cl)c(Cl)c2)c2c', p: '0.015', a: false },
    { i: 5,  s: 'CCOc1ccc(Nc2c3ccccc3nc3ccccc23)cc1.Cl', p: '0.005', a: false },
    { i: 6,  s: 'Cc1ccc2nc(C)cc(Nc3ccc(C(F)(F)F)c3)c2c1.Cl', p: '0.004', a: false },
    { i: 7,  s: 'Br.CCn1c2cc(c(=N)c3c1CCCC3)CCCC2', p: '0.095', a: false },
    { i: 8,  s: 'CCN(CC)CCn1c(=N)n(CC(O)c2ccc(Cl)c(Cl)c2)c2', p: '0.974', a: true },
    { i: 9,  s: 'O=C1OCC(N2CCN(Cc3ccccc3)CC2)c2ccccc21', p: '0.012', a: false },
    { i: 10, s: 'O=C1OCC(N(c2ccccc2)Cc2ccccc2)c2ccccc21', p: '0.018', a: false },
    { i: 11, s: 'CN(CC)CCNc1c2ccccc2nc2ccccc12.Cl', p: '0.961', a: true },
  ];
  const rows = q.data?.molecules?.length
    ? q.data.molecules.map(molecule => ({
      i: molecule.index,
      s: molecule.smiles,
      p: molecule.probability.toFixed(3),
      a: molecule.label === 1 || molecule.probability >= 0.5,
    }))
    : staticRows;
  const total = q.data?.total ?? 1016;
  const nActive = q.data?.n_active ?? 96;
  const nInactive = q.data?.n_inactive ?? 920;
  const accuracy = q.data?.accuracy ?? 1;
  const nPages = q.data?.n_pages ?? 22;
  const shownFrom = total === 0 ? 0 : (page - 1) * 48 + 1;
  const shownTo = Math.min(page * 48, total);
  const exportGrid = () => {
    const csv = ['index,smiles,probability,active', ...rows.map(row => [row.i, `"${row.s.replaceAll('"', '""')}"`, row.p, row.a].join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ragmodex-visualizer-grid.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ width: 1440, height: 1024, position: 'relative', fontFamily: TOKENS.fontText, color: TOKENS.ink }}>
      <MeshBackground style={{ height: '100%', overflow: 'hidden' }}>
        <div style={{ display: 'flex', height: '100%' }}>
          <VizSidebar/>

          <div data-glass-main style={{ flex: 1, height: '100%', overflowY: 'auto', padding: '8px 20px 20px 4px', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
            {/* Top bar */}
            <Glass tone="A" radius={20} padding={0} style={{ marginBottom: 22 }}>
              <VizTopBar/>
            </Glass>

            {/* Hero */}
            <div style={{ padding: '4px 6px 22px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
                <div>
                  <Label style={{ marginBottom: 12, color: TOKENS.accent }}>WORKSPACE - VISUALIZER</Label>
                  <h1 style={{ margin: 0, fontFamily: TOKENS.fontDisplay, fontSize: 56, fontWeight: 700, letterSpacing: '-0.035em', lineHeight: 1, color: TOKENS.ink }}>
                    Molecule Visualizer
                  </h1>
                  <div style={{ marginTop: 14, fontFamily: TOKENS.fontText, fontSize: 15, color: TOKENS.inkMuted, maxWidth: 620, lineHeight: 1.5 }}>
                    Browse training-set predictions with ECFP fingerprint distributions.
                  </div>
                </div>
                <div />
              </div>
            </div>

            {/* Metric tiles */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 22 }}>
              <MetricTile label="Active molecules" value={nActive.toLocaleString()} sub="Class 1 - positives" tone="accent" tiny={`${total ? ((nActive / total) * 100).toFixed(1) : '0.0'}%`}/>
              <MetricTile label="Inactive molecules" value={nInactive.toLocaleString()} sub="Class 0 - negatives" tone="danger" tiny={`${total ? ((nInactive / total) * 100).toFixed(1) : '0.0'}%`}/>
              <MetricTile label="Training accuracy" value={`${(accuracy * 100).toFixed(1)}%`} sub="Current model predictions" tone="info"/>
            </div>

            {/* Distribution */}
            <Glass tone="A" radius={22} padding={22} style={{ marginBottom: 22 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 }}>
                <div>
                  <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>Prediction Distribution</div>
                  <Caption style={{ marginTop: 3 }}>P(active) over 1,016 training molecules. Threshold at 0.5.</Caption>
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted, fontWeight: 600 }}>
                    <span style={{ width: 12, height: 12, borderRadius: 3, background: 'oklch(60% 0.13 155)' }}/> Active
                  </div>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted, fontWeight: 600 }}>
                    <span style={{ width: 12, height: 12, borderRadius: 3, background: 'oklch(62% 0.16 25)' }}/> Inactive
                  </div>
                </div>
              </div>
              <DistChart/>
            </Glass>

            {/* Filter bar */}
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
              <div style={{
                flex: '0 0 320px',
                display: 'flex', alignItems: 'center', gap: 10,
                height: 42, padding: '0 14px',
                background: 'rgba(255,255,255,0.6)',
                borderRadius: 12,
                boxShadow: TOKENS.shadowInput,
              }}>
                <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="search" size={15}/></span>
                <input
                  value={search}
                  onChange={event => {
                    setPage(1);
                    setSearch(event.target.value);
                  }}
                  placeholder="Filter by SMILES..."
                  style={{
                    flex: 1,
                    border: 'none',
                    outline: 'none',
                    background: 'transparent',
                    fontFamily: TOKENS.fontMono, fontSize: 13, color: TOKENS.ink,
                  }}
                />
                <span style={{ display: 'none' }}>Filter by SMILES...</span>
                <span style={{
                  padding: '2px 7px', borderRadius: 5,
                  background: 'rgba(15,18,28,0.05)',
                  fontFamily: TOKENS.fontMono, fontSize: 10, color: TOKENS.inkMuted, fontWeight: 600,
                }}>Ctrl K</span>
              </div>

              {/* All / Active / Inactive */}
              <Glass tone="B" radius={11} padding={3} style={{ display: 'inline-flex', gap: 2 }}>
                {[
                  { label: 'All', value: 'all', count: total },
                  { label: 'Active', value: 'active', count: nActive },
                  { label: 'Inactive', value: 'inactive', count: nInactive },
                ].map((item) => {
                  const active = filterClass === item.value;
                  return (
                  <button key={item.value} type="button" onClick={() => { setPage(1); setFilterClass(item.value); }} style={{
                    appearance: 'none', border: 'none',
                    padding: '7px 14px',
                    borderRadius: 8,
                    background: active ? '#fff' : 'transparent',
                    color: active ? TOKENS.ink : TOKENS.inkMuted,
                    fontFamily: TOKENS.fontText, fontSize: 12.5, fontWeight: 600, letterSpacing: '-0.005em',
                    boxShadow: active ? '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.05), 0 4px 10px -4px rgba(15,18,28,0.12)' : 'none',
                    cursor: 'pointer',
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                  }}>
                    {item.label}
                    {item.value !== 'all' && (
                      <span style={{
                        fontFamily: TOKENS.fontMono, fontSize: 10, color: TOKENS.inkFaint, fontWeight: 600,
                        padding: '1px 6px', borderRadius: 5, background: 'rgba(15,18,28,0.05)',
                      }}>{item.count.toLocaleString()}</span>
                    )}
                  </button>
                )})}
              </Glass>

              {/* Sort */}
              <div style={{
                display: 'flex', alignItems: 'center', gap: 10,
                height: 42, padding: '0 12px 0 14px',
                background: 'rgba(255,255,255,0.6)',
                borderRadius: 12,
                boxShadow: TOKENS.shadowInput,
              }}>
                <Label>Sort</Label>
                <select
                  value={sort}
                  onChange={event => {
                    setPage(1);
                    setSort(event.target.value);
                  }}
                  style={{
                    appearance: 'none',
                    border: 'none',
                    outline: 'none',
                    background: 'transparent',
                    fontFamily: TOKENS.fontText, fontSize: 13, color: TOKENS.ink, fontWeight: 600,
                  }}
                >
                  <option value="default">Default order</option>
                  <option value="prob_desc">P(active) high</option>
                  <option value="prob_asc">P(active) low</option>
                </select>
                <Icon name="chevDown" size={14} color={TOKENS.inkMuted}/>
              </div>

              <div style={{ flex: 1 }}/>

              <div style={{
                padding: '8px 14px',
                background: 'rgba(255,255,255,0.55)',
                borderRadius: 10,
                fontFamily: TOKENS.fontMono, fontSize: 12, color: TOKENS.inkMuted, fontWeight: 600,
                boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
              }}>{shownFrom}-{shownTo} <span style={{ color: TOKENS.inkFaint }}>of</span> {total.toLocaleString()}</div>
            </div>

            {/* Molecule grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
              {rows.map((r) => (
                <MoleculeCard key={r.i} idx={r.i} smiles={r.s} p={r.p} active={r.a}/>
              ))}
            </div>

            {/* Pagination */}
            <div style={{ marginTop: 18, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 6 }}>
              {['prev', 1, 2, 3, '...', Math.max(1, nPages - 1), nPages, 'next'].map((l, i) => {
                const label = l === 'prev' ? '<' : l === 'next' ? '>' : String(l);
                const target = l === 'prev' ? Math.max(1, page - 1) : l === 'next' ? Math.min(nPages, page + 1) : typeof l === 'number' ? l : page;
                const active = l === page;
                const disabled = l === '...' || target === page;
                return (
                  <button key={`${l}-${i}`} type="button" disabled={disabled} onClick={() => setPage(target)} style={{
                    appearance: 'none', border: 'none',
                    minWidth: 34, height: 34, padding: '0 10px',
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    borderRadius: 9,
                    background: active ? '#fff' : 'rgba(255,255,255,0.55)',
                    color: active ? TOKENS.ink : TOKENS.inkMuted,
                    fontFamily: TOKENS.fontMono, fontSize: 12.5, fontWeight: 700,
                    boxShadow: active ? '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.05), 0 4px 10px -4px rgba(15,18,28,0.12)' : '0 0 0 1px rgba(15,18,28,0.05)',
                    cursor: disabled ? 'default' : 'pointer',
                    opacity: l === '...' ? 0.65 : 1,
                  }}>{label}</button>
                );
              })}
            </div>
          </div>
        </div>
      </MeshBackground>
    </div>
  );
};

export default VisualizerPage;





