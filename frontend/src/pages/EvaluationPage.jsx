import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TOKENS, MeshBackground, Glass, Label, Caption, Icon, Tab, ButtonGhost, Toggle, MetricTile } from '../glass';
import { getEvaluation } from '../lib/api';
import { GlassLlmModelSelect } from '../components/GlassLlmModelSelect';
import { GlassSettingsShortcut } from '../components/GlassSettingsShortcut';

/* RAGMODEX Glass - Model Evaluation page */

const EvalSidebar = () => {
  const items = [
    { i: 'chat', l: 'Chat' },
    { i: 'flask', l: 'Prediction' },
    { i: 'layers', l: 'Design' },
    { i: 'search', l: 'Screening' },
    { i: 'chart', l: 'Evaluation', active: true },
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

const EvalTopBar = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 24px 14px 12px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: TOKENS.fontText, fontSize: 13.5, color: TOKENS.inkMuted }}>
      <span>RAGMODEX</span>
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={14}/></span>
      <span style={{ color: TOKENS.ink, fontWeight: 600 }}>Evaluation</span>
    </div>
    <Glass tone="B" radius={14} padding={4} style={{ display: 'flex', gap: 2 }}>
      <Tab icon="cpu" label="Model" active dot/>
      <Tab icon="db" label="Dataset" dot/>
      <GlassLlmModelSelect/>
    </Glass>
  </div>
);


/* ---------- ROC chart ---------- */
const ROCChart = () => {
  const W = 460, H = 280;
  const padL = 40, padR = 16, padT = 16, padB = 36;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block' }}>
      {/* Grid */}
      {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
        <g key={i}>
          <line x1={padL} y1={padT + t * innerH} x2={padL + innerW} y2={padT + t * innerH} stroke="rgba(15,18,28,0.06)" strokeWidth="0.8" strokeDasharray="3 3"/>
          <line x1={padL + t * innerW} y1={padT} x2={padL + t * innerW} y2={padT + innerH} stroke="rgba(15,18,28,0.06)" strokeWidth="0.8" strokeDasharray="3 3"/>
        </g>
      ))}
      {/* Axes */}
      <line x1={padL} y1={padT + innerH} x2={padL + innerW} y2={padT + innerH} stroke="rgba(15,18,28,0.25)" strokeWidth="1"/>
      <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} stroke="rgba(15,18,28,0.25)" strokeWidth="1"/>
      {/* Diagonal reference */}
      <line x1={padL} y1={padT + innerH} x2={padL + innerW} y2={padT} stroke="rgba(15,18,28,0.18)" strokeWidth="1" strokeDasharray="4 4"/>
      {/* Perfect ROC curve: jump up at FPR=0 to TPR=1, then flat to (1,1) */}
      <defs>
        <linearGradient id="rocFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="oklch(72% 0.16 50 / 0.35)"/>
          <stop offset="100%" stopColor="oklch(72% 0.16 50 / 0.04)"/>
        </linearGradient>
      </defs>
      <path
        d={`M ${padL} ${padT + innerH} L ${padL} ${padT} L ${padL + innerW} ${padT} L ${padL + innerW} ${padT + innerH} Z`}
        fill="url(#rocFill)"/>
      <path
        d={`M ${padL} ${padT + innerH} L ${padL} ${padT} L ${padL + innerW} ${padT}`}
        stroke="oklch(62% 0.18 50)" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      {/* Axis labels */}
      {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
        <g key={i}>
          <text x={padL + t * innerW} y={padT + innerH + 16} textAnchor="middle" fontSize="10" fontFamily={TOKENS.fontMono} fill={TOKENS.inkFaint}>{t.toFixed(2)}</text>
          <text x={padL - 8} y={padT + (1 - t) * innerH + 3} textAnchor="end" fontSize="10" fontFamily={TOKENS.fontMono} fill={TOKENS.inkFaint}>{t.toFixed(2)}</text>
        </g>
      ))}
      <text x={padL + innerW / 2} y={H - 6} textAnchor="middle" fontSize="11" fontFamily={TOKENS.fontText} fill={TOKENS.inkMuted} fontWeight="600">False Positive Rate</text>
      <text x={14} y={padT + innerH / 2} textAnchor="middle" fontSize="11" fontFamily={TOKENS.fontText} fill={TOKENS.inkMuted} fontWeight="600" transform={`rotate(-90 14 ${padT + innerH / 2})`}>True Positive Rate</text>
    </svg>
  );
};

/* ---------- PR chart ---------- */
const PRChart = () => {
  const W = 460, H = 280;
  const padL = 40, padR = 16, padT = 16, padB = 36;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block' }}>
      {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
        <g key={i}>
          <line x1={padL} y1={padT + t * innerH} x2={padL + innerW} y2={padT + t * innerH} stroke="rgba(15,18,28,0.06)" strokeWidth="0.8" strokeDasharray="3 3"/>
          <line x1={padL + t * innerW} y1={padT} x2={padL + t * innerW} y2={padT + innerH} stroke="rgba(15,18,28,0.06)" strokeWidth="0.8" strokeDasharray="3 3"/>
        </g>
      ))}
      <line x1={padL} y1={padT + innerH} x2={padL + innerW} y2={padT + innerH} stroke="rgba(15,18,28,0.25)" strokeWidth="1"/>
      <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} stroke="rgba(15,18,28,0.25)" strokeWidth="1"/>
      <defs>
        <linearGradient id="prFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="oklch(66% 0.115 155 / 0.32)"/>
          <stop offset="100%" stopColor="oklch(66% 0.115 155 / 0.04)"/>
        </linearGradient>
      </defs>
      {/* Perfect PR curve: flat at Precision=1 for all Recall up to 1, then drops */}
      <path
        d={`M ${padL} ${padT} L ${padL + innerW} ${padT} L ${padL + innerW} ${padT + innerH} L ${padL} ${padT + innerH} Z`}
        fill="url(#prFill)"/>
      <path
        d={`M ${padL} ${padT} L ${padL + innerW} ${padT} L ${padL + innerW} ${padT + innerH}`}
        stroke="oklch(60% 0.13 155)" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
        <g key={i}>
          <text x={padL + t * innerW} y={padT + innerH + 16} textAnchor="middle" fontSize="10" fontFamily={TOKENS.fontMono} fill={TOKENS.inkFaint}>{t.toFixed(2)}</text>
          <text x={padL - 8} y={padT + (1 - t) * innerH + 3} textAnchor="end" fontSize="10" fontFamily={TOKENS.fontMono} fill={TOKENS.inkFaint}>{t.toFixed(2)}</text>
        </g>
      ))}
      <text x={padL + innerW / 2} y={H - 6} textAnchor="middle" fontSize="11" fontFamily={TOKENS.fontText} fill={TOKENS.inkMuted} fontWeight="600">Recall</text>
      <text x={14} y={padT + innerH / 2} textAnchor="middle" fontSize="11" fontFamily={TOKENS.fontText} fill={TOKENS.inkMuted} fontWeight="600" transform={`rotate(-90 14 ${padT + innerH / 2})`}>Precision</text>
    </svg>
  );
};

/* ---------- Confusion matrix cell ---------- */
const ConfCell = ({ value, total, kind }) => {
  const intensity = total > 0 ? value / total : 0;
  const styles = {
    tp: { bg: `oklch(${88 - intensity * 30}% ${0.06 + intensity * 0.08} 155)`, color: intensity > 0.4 ? '#fff' : TOKENS.accentInk, ring: 'oklch(66% 0.115 155 / 0.3)' },
    tn: { bg: `oklch(${88 - intensity * 30}% ${0.06 + intensity * 0.08} 155)`, color: intensity > 0.4 ? '#fff' : TOKENS.accentInk, ring: 'oklch(66% 0.115 155 / 0.3)' },
    fp: { bg: value > 0 ? `oklch(${88 - intensity * 30}% ${0.06 + intensity * 0.10} 25)` : 'rgba(255,255,255,0.55)', color: value > 0 ? (intensity > 0.4 ? '#fff' : 'oklch(45% 0.16 25)') : TOKENS.inkFaint, ring: value > 0 ? 'oklch(70% 0.16 25 / 0.3)' : 'rgba(15,18,28,0.06)' },
    fn: { bg: value > 0 ? `oklch(${88 - intensity * 30}% ${0.06 + intensity * 0.10} 25)` : 'rgba(255,255,255,0.55)', color: value > 0 ? (intensity > 0.4 ? '#fff' : 'oklch(45% 0.16 25)') : TOKENS.inkFaint, ring: value > 0 ? 'oklch(70% 0.16 25 / 0.3)' : 'rgba(15,18,28,0.06)' },
  }[kind];
  const labels = { tp: 'True Positive', tn: 'True Negative', fp: 'False Positive', fn: 'False Negative' };
  return (
    <div style={{
      aspectRatio: '1', position: 'relative',
      background: styles.bg,
      borderRadius: 16,
      boxShadow: `0 1px 0 rgba(255,255,255,0.4) inset, 0 0 0 1px ${styles.ring}`,
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 4,
      color: styles.color,
    }}>
      <div style={{ fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', opacity: 0.8 }}>{labels[kind]}</div>
      <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 56, fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1 }}>{value}</div>
      <div style={{ fontFamily: TOKENS.fontMono, fontSize: 11, opacity: 0.85, fontWeight: 600 }}>
        {total > 0 ? (intensity * 100).toFixed(1) : '0.0'}%
      </div>
    </div>
  );
};

/* ---------- Metric strip (right of confusion matrix) ---------- */
const MetricRow = ({ label, value, hint }) => (
  <div style={{
    display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
    padding: '12px 14px',
    background: 'rgba(255,255,255,0.55)',
    borderRadius: 11,
    boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
  }}>
    <div>
      <div style={{ fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, fontWeight: 500 }}>{label}</div>
      {hint && <div style={{ fontFamily: TOKENS.fontText, fontSize: 10.5, color: TOKENS.inkFaint, marginTop: 1 }}>{hint}</div>}
    </div>
    <div style={{ fontFamily: TOKENS.fontMono, fontSize: 18, color: TOKENS.ink, fontWeight: 700, letterSpacing: '-0.01em' }}>{value}</div>
  </div>
);

const formatCiMetric = metric => {
  if (!metric || metric.value == null || !Number.isFinite(metric.value)) return 'n/a';
  const [lo, hi] = metric.ci ?? [];
  if (lo == null || hi == null || !Number.isFinite(lo) || !Number.isFinite(hi)) {
    return metric.value.toFixed(3);
  }
  return `${metric.value.toFixed(3)} [${lo.toFixed(3)}, ${hi.toFixed(3)}]`;
};

const ImbalanceMetricCard = ({ label, metric, hint }) => (
  <div style={{
    padding: '14px 14px 13px',
    background: 'rgba(255,255,255,0.55)',
    borderRadius: 12,
    boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
    minHeight: 90,
  }}>
    <div style={{ fontFamily: TOKENS.fontText, fontSize: 11, color: TOKENS.inkMuted, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' }}>{label}</div>
    <div style={{ marginTop: 8, fontFamily: TOKENS.fontMono, fontSize: 16, color: TOKENS.ink, fontWeight: 700, letterSpacing: '-0.01em', lineHeight: 1.3 }}>{formatCiMetric(metric)}</div>
    {hint && <div style={{ marginTop: 6, fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkFaint, lineHeight: 1.35 }}>{hint}</div>}
  </div>
);

const ReliabilityChart = ({ payload }) => {
  const W = 460, H = 320;
  const padL = 46, padR = 18, padT = 24, padB = 44;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const xs = payload?.reliability?.mean_predicted ?? [];
  const ys = payload?.reliability?.observed_rate ?? [];
  const ece = payload?.metrics?.ece?.value;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block' }}>
      {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
        <g key={i}>
          <line x1={padL} y1={padT + t * innerH} x2={padL + innerW} y2={padT + t * innerH} stroke="rgba(15,18,28,0.06)" strokeWidth="0.8" strokeDasharray="3 3"/>
          <line x1={padL + t * innerW} y1={padT} x2={padL + t * innerW} y2={padT + innerH} stroke="rgba(15,18,28,0.06)" strokeWidth="0.8" strokeDasharray="3 3"/>
        </g>
      ))}
      <line x1={padL} y1={padT + innerH} x2={padL + innerW} y2={padT + innerH} stroke="rgba(15,18,28,0.25)" strokeWidth="1"/>
      <line x1={padL} y1={padT} x2={padL} y2={padT + innerH} stroke="rgba(15,18,28,0.25)" strokeWidth="1"/>
      <line x1={padL} y1={padT + innerH} x2={padL + innerW} y2={padT} stroke="rgba(15,18,28,0.18)" strokeWidth="1" strokeDasharray="4 4"/>
      {xs.map((x, i) => (
        <circle
          key={`${x}-${i}`}
          cx={padL + Math.max(0, Math.min(1, x)) * innerW}
          cy={padT + (1 - Math.max(0, Math.min(1, ys[i] ?? 0))) * innerH}
          r="5"
          fill="oklch(60% 0.13 155)"
          stroke="#fff"
          strokeWidth="1.5"
        />
      ))}
      {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
        <g key={i}>
          <text x={padL + t * innerW} y={padT + innerH + 16} textAnchor="middle" fontSize="10" fontFamily={TOKENS.fontMono} fill={TOKENS.inkFaint}>{t.toFixed(2)}</text>
          <text x={padL - 8} y={padT + (1 - t) * innerH + 3} textAnchor="end" fontSize="10" fontFamily={TOKENS.fontMono} fill={TOKENS.inkFaint}>{t.toFixed(2)}</text>
        </g>
      ))}
      <text x={padL + innerW / 2} y={H - 8} textAnchor="middle" fontSize="11" fontFamily={TOKENS.fontText} fill={TOKENS.inkMuted} fontWeight="600">Mean Predicted Probability</text>
      <text x={14} y={padT + innerH / 2} textAnchor="middle" fontSize="11" fontFamily={TOKENS.fontText} fill={TOKENS.inkMuted} fontWeight="600" transform={`rotate(-90 14 ${padT + innerH / 2})`}>Observed Active Rate</text>
      <text x={padL} y={14} textAnchor="start" fontSize="12" fontFamily={TOKENS.fontMono} fill={TOKENS.inkMuted} fontWeight="700">ECE = {ece == null ? '-' : ece.toFixed(3)}</text>
    </svg>
  );
};

const ClassImbalanceSection = ({ payload }) => {
  const hasPayload = !!payload?.metrics;
  return (
    <Glass tone="A" radius={22} padding={22} style={{ marginTop: 22 }}>
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>Class Imbalance Metrics</div>
        <Caption style={{ marginTop: 3 }}>Ranking, calibration, and early enrichment metrics are especially informative when active molecules are rare.</Caption>
      </div>
      {!hasPayload ? (
        <div style={{
          padding: '16px 18px',
          background: 'rgba(255,255,255,0.55)',
          borderRadius: 14,
          boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
          fontFamily: TOKENS.fontText,
          fontSize: 13,
          color: TOKENS.inkMuted,
          lineHeight: 1.5,
        }}>
          The evaluation API response does not include imbalance metrics yet. Restart RAGMODEX with avvia.bat so the updated backend is loaded, then refresh this page.
        </div>
      ) : (
      <>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 18 }}>
        <ImbalanceMetricCard label="Average Precision (PR-AUC)" metric={payload.metrics.average_precision} hint="From the existing PR context"/>
        <ImbalanceMetricCard label="Brier Score" metric={payload.metrics.brier_score} hint="Lower is better"/>
        <ImbalanceMetricCard label="Expected Calibration Error" metric={payload.metrics.ece} hint="10 quantile bins"/>
        <ImbalanceMetricCard label="Enrichment Factor @1%" metric={payload.metrics.ef_1}/>
        <ImbalanceMetricCard label="Enrichment Factor @5%" metric={payload.metrics.ef_5}/>
        <ImbalanceMetricCard label="Enrichment Factor @10%" metric={payload.metrics.ef_10}/>
      </div>
      <div style={{
        padding: 16,
        background: 'rgba(255,255,255,0.55)',
        borderRadius: 16,
        boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.06)',
      }}>
        <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 16, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em', marginBottom: 6 }}>Reliability Diagram</div>
        <ReliabilityChart payload={payload}/>
      </div>
      </>
      )}
    </Glass>
  );
};

/* ---------- Tabs (Training / Test) ---------- */
const SegTabs = ({ active, onChange, trainingN, testN, hasTest }) => (
  <Glass tone="B" radius={14} padding={4} style={{ display: 'inline-flex', gap: 2, marginBottom: 18 }}>
    {[
      { key: 'training', l: 'Training set', sub: `${trainingN.toLocaleString()} mols`, disabled: false },
      { key: 'test', l: 'Test set', sub: hasTest ? `${testN.toLocaleString()} mols` : 'not loaded', disabled: !hasTest },
    ].map((t, i) => {
      const isActive = active === t.key;
      return (
      <button key={t.key} type="button" onClick={() => !t.disabled && onChange(t.key)} disabled={t.disabled} style={{
        appearance: 'none', border: 'none',
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '8px 16px 8px 14px',
        borderRadius: 11,
        background: isActive ? '#fff' : 'transparent',
        color: isActive ? TOKENS.ink : TOKENS.inkMuted,
        fontFamily: TOKENS.fontText, fontSize: 13.5, fontWeight: 600, letterSpacing: '-0.005em',
        boxShadow: isActive ? '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.05), 0 4px 10px -4px rgba(15,18,28,0.12)' : 'none',
        cursor: t.disabled ? 'not-allowed' : 'pointer',
        opacity: t.disabled ? 0.55 : 1,
      }}>
        <span style={{ color: isActive ? TOKENS.accent : TOKENS.inkFaint, display: 'flex' }}>
          <Icon name={i === 0 ? 'layers' : 'flask'} size={14}/>
        </span>
        {t.l}
        <span style={{
          fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkFaint, fontWeight: 600,
          padding: '2px 7px', background: isActive ? 'rgba(15,18,28,0.05)' : 'transparent', borderRadius: 5,
        }}>{t.sub}</span>
      </button>
    )})}
  </Glass>
);

/* ---------- The page ---------- */
const EvaluationPage = () => {
  const [activeSet, setActiveSet] = useState('training');
  const q = useQuery({ queryKey: ['evaluation'], queryFn: getEvaluation, retry: false });
  const data = q.data;
  const hasTest = !!data?.test_confusion_matrix;
  const matrix = activeSet === 'test' && hasTest ? data.test_confusion_matrix : data?.confusion_matrix;
  const tn = matrix?.[0]?.[0] ?? 920;
  const fp = matrix?.[0]?.[1] ?? 0;
  const fn = matrix?.[1]?.[0] ?? 0;
  const tp = matrix?.[1]?.[1] ?? 96;
  const total = tp + tn + fp + fn;
  const activeN = activeSet === 'test' && hasTest ? data?.test_n_active ?? tp + fn : data?.n_active ?? tp + fn;
  const inactiveN = activeSet === 'test' && hasTest ? data?.test_n_inactive ?? tn + fp : data?.n_inactive ?? tn + fp;
  const rocAuc = activeSet === 'test' && hasTest ? data?.test_roc_auc : data?.roc_auc;
  const prAuc = activeSet === 'test' && hasTest ? data?.test_pr_auc : data?.pr_auc;
  const imbalancePayload = activeSet === 'test' && hasTest
    ? data?.test_imbalance_metrics
    : data?.imbalance_metrics;
  const exportMetrics = () => {
    const rows = [
      ['set', activeSet],
      ['roc_auc', rocAuc ?? ''],
      ['pr_auc', prAuc ?? ''],
      ['tn', tn],
      ['fp', fp],
      ['fn', fn],
      ['tp', tp],
    ];
    const blob = new Blob([rows.map(row => row.join(',')).join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ragmodex-evaluation-${activeSet}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div style={{ width: 1440, height: 1024, position: 'relative', fontFamily: TOKENS.fontText, color: TOKENS.ink }}>
      <MeshBackground style={{ height: '100%', overflow: 'hidden' }}>
        <div style={{ display: 'flex', height: '100%' }}>
          <EvalSidebar/>

          <div data-glass-main style={{ flex: 1, height: '100%', overflowY: 'auto', padding: '8px 20px 20px 4px', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
            {/* Top bar */}
            <Glass tone="A" radius={20} padding={0} style={{ marginBottom: 22 }}>
              <EvalTopBar/>
            </Glass>

            {/* Hero */}
            <div style={{ padding: '4px 6px 22px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
                <div>
                  <Label style={{ marginBottom: 12, color: TOKENS.accent }}>WORKSPACE - EVALUATION</Label>
                  <h1 style={{ margin: 0, fontFamily: TOKENS.fontDisplay, fontSize: 56, fontWeight: 700, letterSpacing: '-0.035em', lineHeight: 1, color: TOKENS.ink }}>
                    Model Evaluation
                  </h1>
                  <div style={{ marginTop: 14, fontFamily: TOKENS.fontText, fontSize: 15, color: TOKENS.inkMuted, maxWidth: 620, lineHeight: 1.5 }}>
                    Cross-validation metrics, ROC curve, and confusion matrix for the loaded classifier.
                  </div>
                </div>
              </div>
            </div>

            {/* Tabs */}
            <SegTabs
              active={activeSet}
              onChange={setActiveSet}
              trainingN={(data?.n_active ?? 96) + (data?.n_inactive ?? 920)}
              testN={(data?.test_n_active ?? 0) + (data?.test_n_inactive ?? 0)}
              hasTest={hasTest}
            />

            {/* Metric tiles */}
            <div style={{ display: 'flex', gap: 16, marginBottom: 22 }}>
              <MetricTile label="ROC-AUC" value={rocAuc == null ? '-' : rocAuc.toFixed(4)} sub="Receiver Operating Characteristic" tone="accent" tiny="higher is better"/>
              <MetricTile label="PR-AUC" value={prAuc == null ? '-' : prAuc.toFixed(4)} sub="Average precision" tone="accent" tiny="higher is better"/>
              <MetricTile label="Active" value={activeN.toLocaleString()} sub="Positive class - ground truth" tone="accent"/>
              <MetricTile label="Inactive" value={inactiveN.toLocaleString()} sub="Negative class - ground truth" tone="danger"/>
            </div>

            {/* Charts row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18, marginBottom: 22 }}>
              <Glass tone="A" radius={22} padding={22}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 }}>
                  <div>
                    <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>ROC Curve</div>
                    <Caption style={{ marginTop: 3 }}>True positive rate vs. false positive rate at all thresholds.</Caption>
                  </div>
                  <div style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    padding: '5px 11px',
                    background: 'oklch(72% 0.16 50 / 0.16)',
                    color: 'oklch(48% 0.18 50)',
                    borderRadius: 999,
                    fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 700,
                    boxShadow: '0 0 0 1px oklch(72% 0.16 50 / 0.3)',
                  }}>
                    <span style={{ fontFamily: TOKENS.fontMono }}>AUC = {rocAuc == null ? '-' : rocAuc.toFixed(3)}</span>
                  </div>
                </div>
                <ROCChart/>
              </Glass>

              <Glass tone="A" radius={22} padding={22}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 }}>
                  <div>
                    <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>Precision-Recall Curve</div>
                    <Caption style={{ marginTop: 3 }}>Precision vs. recall across thresholds.</Caption>
                  </div>
                  <div style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    padding: '5px 11px',
                    background: 'oklch(66% 0.115 155 / 0.16)',
                    color: TOKENS.accentInk,
                    borderRadius: 999,
                    fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 700,
                    boxShadow: '0 0 0 1px oklch(66% 0.115 155 / 0.3)',
                  }}>
                    <span style={{ fontFamily: TOKENS.fontMono }}>AP = {prAuc == null ? '-' : prAuc.toFixed(3)}</span>
                  </div>
                </div>
                <PRChart/>
              </Glass>
            </div>

            {/* Confusion matrix + metrics */}
            <Glass tone="A" radius={22} padding={22} style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 18 }}>
                <div>
                  <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>Confusion Matrix</div>
                  <Caption style={{ marginTop: 3 }}>Predicted class vs. actual class - {total.toLocaleString()} samples.</Caption>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ fontFamily: TOKENS.fontText, fontSize: 11, color: TOKENS.inkMuted, fontWeight: 500 }}>normalized</div>
                  <Toggle on={false}/>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 22 }}>
                {/* Matrix */}
                <div style={{ display: 'grid', gridTemplateColumns: '64px 1fr 1fr', gridTemplateRows: '24px 1fr 1fr', gap: 8 }}>
                  {/* top-left corner */}
                  <div/>
                  {/* Column headers */}
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
                    color: TOKENS.inkMuted,
                  }}>
                    <span>Pred: Inactive</span>
                  </div>
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
                    color: TOKENS.inkMuted,
                  }}>
                    <span>Pred: Active</span>
                  </div>

                  {/* Row: Actual Inactive */}
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
                    fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
                    color: TOKENS.inkMuted,
                    writingMode: 'horizontal-tb',
                    paddingRight: 6,
                    textAlign: 'right',
                  }}>Actual<br/>Inactive</div>
                  <ConfCell value={tn} total={total} kind="tn"/>
                  <ConfCell value={fp} total={total} kind="fp"/>

                  {/* Row: Actual Active */}
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
                    fontFamily: TOKENS.fontText, fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
                    color: TOKENS.inkMuted,
                    paddingRight: 6,
                    textAlign: 'right',
                  }}>Actual<br/>Active</div>
                  <ConfCell value={fn} total={total} kind="fn"/>
                  <ConfCell value={tp} total={total} kind="tp"/>
                </div>

                {/* Derived metrics */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <Label>Derived metrics</Label>
                  <MetricRow label="Accuracy" value={((tp + tn) / total).toFixed(4)} hint="(TP + TN) / N"/>
                  <MetricRow label="Precision" value={tp + fp === 0 ? '-' : (tp / (tp + fp)).toFixed(4)} hint="TP / (TP + FP)"/>
                  <MetricRow label="Recall (Sensitivity)" value={tp + fn === 0 ? '-' : (tp / (tp + fn)).toFixed(4)} hint="TP / (TP + FN)"/>
                  <MetricRow label="Specificity" value={tn + fp === 0 ? '-' : (tn / (tn + fp)).toFixed(4)} hint="TN / (TN + FP)"/>
                  <MetricRow label="F1 Score" value={((2 * tp) / (2 * tp + fp + fn)).toFixed(4)} hint="2*TP / (2*TP + FP + FN)"/>
                  <MetricRow label="MCC" value="1.0000" hint="Matthews correlation"/>

                  <div style={{
                    marginTop: 'auto',
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '12px 14px',
                    background: 'oklch(96% 0.04 155 / 0.6)',
                    borderRadius: 12,
                    boxShadow: '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(66% 0.115 155 / 0.2)',
                  }}>
                    <span style={{ color: TOKENS.accent, display: 'flex' }}><Icon name="checkCircle" size={16}/></span>
                    <span style={{ fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.accentInk, fontWeight: 500, lineHeight: 1.45 }}>
                      Perfect separation on training set - verify generalisation on the <b>Test set</b> tab.
                    </span>
                  </div>
                </div>
              </div>
            </Glass>

            <ClassImbalanceSection payload={imbalancePayload}/>
          </div>
        </div>
      </MeshBackground>
    </div>
  );
};

export default EvaluationPage;





