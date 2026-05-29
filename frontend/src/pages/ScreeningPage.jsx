import { useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { TOKENS, MeshBackground, Glass, Label, Caption, Icon, Tab } from '../glass';
import { moleculeImageUrl, runScreening } from '../lib/api';
import { GlassLlmModelSelect } from '../components/GlassLlmModelSelect';
import { GlassSettingsShortcut } from '../components/GlassSettingsShortcut';

/* RAGMODEX Glass - Virtual Screening */

const SCREENING_STATE_KEY = 'ragmodex_screening_state';

function loadScreeningState() {
  try {
    const raw = localStorage.getItem(SCREENING_STATE_KEY);
    return raw ? JSON.parse(raw) : { results: [], fileName: '' };
  } catch {
    return { results: [], fileName: '' };
  }
}

function saveScreeningState(state) {
  try {
    localStorage.setItem(SCREENING_STATE_KEY, JSON.stringify(state));
  } catch {}
}

const ScrSidebar = () => {
  const items = [
    { i: 'chat', l: 'Chat' },
    { i: 'flask', l: 'Prediction' },
    { i: 'layers', l: 'Design' },
    { i: 'search', l: 'Screening', active: true },
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

const ScrTopBar = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 24px 14px 12px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: TOKENS.fontText, fontSize: 13.5, color: TOKENS.inkMuted }}>
      <span>RAGMODEX</span>
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={14}/></span>
      <span style={{ color: TOKENS.ink, fontWeight: 600 }}>Screening</span>
    </div>
    <Glass tone="B" radius={14} padding={4} style={{ display: 'flex', gap: 2 }}>
      <Tab icon="cpu" label="Model" active dot/>
      <Tab icon="db" label="Dataset" dot/>
      <GlassLlmModelSelect/>
    </Glass>
  </div>
);

/* ---------- Schema row ---------- */
const SchemaRow = ({ k, v, mono }) => (
  <div style={{
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '10px 12px',
    background: 'rgba(255,255,255,0.55)',
    borderRadius: 10,
    boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
  }}>
    <span style={{ fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, fontWeight: 500 }}>{k}</span>
    <span style={{ fontFamily: mono ? TOKENS.fontMono : TOKENS.fontText, fontSize: 12.5, color: TOKENS.ink, fontWeight: 700 }}>{v}</span>
  </div>
);

/* ---------- The page ---------- */
const ScreeningPage = () => {
  const inputRef = useRef(null);
  const [initialState] = useState(loadScreeningState);
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState(initialState.fileName ?? '');
  const [results, setResults] = useState(initialState.results ?? []);
  const [hovered, setHovered] = useState(null);
  const mut = useMutation({
    mutationFn: () => runScreening(file),
    onMutate: () => setResults([]),
    onSuccess: data => {
      const nextResults = data.results ?? [];
      setResults(nextResults);
      saveScreeningState({ results: nextResults, fileName: file?.name ?? fileName });
    },
  });
  const hasResults = results.length > 0;
  const validResults = results.filter(r => r.valid);
  const activeResults = results.filter(r => String(r.prediction).toLowerCase() === 'active');
  const pageHeight = hasResults ? Math.max(1120, 820 + Math.min(results.length, 12) * 52) : 1080;

  const selectFile = nextFile => {
    setFile(nextFile);
    setFileName(nextFile?.name ?? '');
    setResults([]);
    saveScreeningState({ results: [], fileName: nextFile?.name ?? '' });
    mut.reset();
    if (!nextFile && inputRef.current) inputRef.current.value = '';
  };

  useEffect(() => {
    saveScreeningState({ results, fileName });
  }, [results, fileName]);

  const resultRows = results.map((r, index) => ({
    name: r.smiles,
    n: r.valid && r.probability != null ? `${(r.probability * 100).toFixed(1)}%` : 'invalid',
    when: r.prediction ?? 'Invalid',
    hit: r.valid ? (String(r.prediction).toLowerCase() === 'active' ? 'Active' : 'Inactive') : 'Invalid',
    tone: String(r.prediction).toLowerCase() === 'active' ? 'active' : String(r.prediction).toLowerCase() === 'inactive' ? 'inactive' : 'invalid',
    key: `${r.smiles}-${index}`,
  }));

  const pasteSmiles = () => {
    const pasted = window.prompt('Paste one SMILES per line');
    if (!pasted?.trim()) return;
    selectFile(new File([pasted.trim()], 'pasted-smiles.smi', { type: 'text/plain' }));
  };

  const downloadCsv = () => {
    if (!results.length) return;
    const csv = ['smiles,probability,prediction,valid', ...results.map(r => `${r.smiles},${r.probability ?? ''},${r.prediction ?? ''},${r.valid}`)].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = 'screening_results.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
  <div style={{ width: 1440, height: 1024, position: 'relative', fontFamily: TOKENS.fontText, color: TOKENS.ink }}>
    <input
      ref={inputRef}
      type="file"
      accept=".csv,.txt,.smi"
      style={{ display: 'none' }}
      onChange={event => selectFile(event.target.files?.[0] ?? null)}
    />
    <MeshBackground style={{ height: '100%', overflow: 'hidden' }}>
      <div style={{ display: 'flex', height: '100%' }}>
        <ScrSidebar/>

        <div data-glass-main style={{ flex: 1, height: '100%', overflowY: 'auto', padding: '8px 20px 20px 4px', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          {/* Top bar */}
          <Glass tone="A" radius={20} padding={0} style={{ marginBottom: 22 }}>
            <ScrTopBar/>
          </Glass>

          {/* Hero */}
          <div style={{ padding: '4px 6px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
              <div>
                <Label style={{ marginBottom: 12, color: TOKENS.accent }}>WORKSPACE - SCREENING</Label>
                <h1 style={{ margin: 0, fontFamily: TOKENS.fontDisplay, fontSize: 56, fontWeight: 700, letterSpacing: '-0.035em', lineHeight: 1, color: TOKENS.ink }}>
                  Virtual Screening
                </h1>
                <div style={{ marginTop: 14, fontFamily: TOKENS.fontText, fontSize: 15, color: TOKENS.inkMuted, maxWidth: 620, lineHeight: 1.5 }}>
                  Batch SMILES prediction from <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.inkSoft }}>.csv</span>, <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.inkSoft }}>.txt</span>, or <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.inkSoft }}>.smi</span> files.
                </div>
              </div>
            </div>
          </div>

          {/* Main two-column layout */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: 22, flex: 1, minHeight: 0 }}>
            {/* LEFT: dropzone card */}
            <Glass tone="A" radius={26} padding={28} style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                <div>
                  <Label style={{ marginBottom: 8, color: TOKENS.accent }}>BATCH INTAKE</Label>
                  <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 28, fontWeight: 700, color: TOKENS.ink, letterSpacing: '-0.02em' }}>
                    Screen a molecular library
                  </div>
                  <Caption style={{ marginTop: 6 }}>Upload a SMILES list and run the current model across the full set.</Caption>
                </div>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '6px 12px',
                  background: 'rgba(255,255,255,0.6)',
                  borderRadius: 999,
                  boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
                }}>
                  <span style={{ fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: TOKENS.inkMuted }}>Queue</span>
                  <span style={{ fontFamily: TOKENS.fontMono, fontSize: 13, color: TOKENS.ink, fontWeight: 700 }}>{String(file ? 1 : 0).padStart(2, '0')}</span>
                </div>
              </div>

              {/* Dropzone */}
              <div style={{
                flex: 1, position: 'relative',
                border: '2px dashed rgba(15,18,28,0.18)',
                borderRadius: 20,
                background: 'rgba(255,255,255,0.35)',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 14,
                padding: 40,
                overflow: 'hidden',
              }}>
                {/* Subtle decorative atoms in corners */}
                <svg style={{ position: 'absolute', top: 20, left: 20, opacity: 0.45 }} width="56" height="32" viewBox="0 0 56 32" fill="none" stroke={TOKENS.inkFaint} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 24 L18 8 L32 24 L46 8"/>
                </svg>
                <svg style={{ position: 'absolute', top: 20, right: 24, opacity: 0.45 }} width="56" height="32" viewBox="0 0 56 32" fill="none" stroke={TOKENS.inkFaint} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 8 L18 24 L32 8 L46 24"/>
                </svg>
                <svg style={{ position: 'absolute', bottom: 24, left: 30, opacity: 0.45 }} width="48" height="32" viewBox="0 0 48 32" fill="none" stroke={TOKENS.inkFaint} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="14" cy="16" r="8"/>
                  <path d="M22 16 L36 16"/>
                </svg>
                <svg style={{ position: 'absolute', bottom: 24, right: 26, opacity: 0.45 }} width="48" height="32" viewBox="0 0 48 32" fill="none" stroke={TOKENS.inkFaint} strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 16 L20 16"/>
                  <circle cx="32" cy="16" r="8"/>
                </svg>

                <div style={{
                  width: 76, height: 76, borderRadius: 22,
                  background: 'linear-gradient(180deg, oklch(86% 0.13 220 / 0.85), oklch(74% 0.13 230 / 0.75))',
                  display: 'grid', placeItems: 'center',
                  color: '#fff',
                  boxShadow: '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(70% 0.13 230 / 0.4), 0 16px 36px -10px oklch(60% 0.15 230 / 0.4)',
                }}>
                  <Icon name="upload" size={32} stroke={1.8}/>
                </div>

                <div style={{ textAlign: 'center', maxWidth: 460 }}>
                  <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 26, fontWeight: 700, color: TOKENS.ink, letterSpacing: '-0.02em' }}>
                    {file?.name ?? fileName ?? 'Drop your screening file'}
                  </div>
                  <div style={{ marginTop: 8, fontFamily: TOKENS.fontText, fontSize: 13.5, color: TOKENS.inkMuted, lineHeight: 1.5 }}>
                    CSV with a <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.inkSoft }}>smiles</span> column, plain TXT, or SMI.<br/>
                    The file is staged locally before the model run.
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                  <button onClick={() => inputRef.current?.click()} style={{
                    appearance: 'none', border: 'none', cursor: 'pointer',
                    padding: '9px 18px',
                    borderRadius: 11,
                    background: '#fff',
                    color: TOKENS.ink,
                    fontFamily: TOKENS.fontText, fontSize: 13, fontWeight: 600, letterSpacing: '-0.005em',
                    boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.07), 0 4px 10px -4px rgba(15,18,28,0.12)',
                  }}>Browse file</button>
                  <button onClick={pasteSmiles} style={{
                    appearance: 'none', border: 'none', cursor: 'pointer',
                    padding: '9px 18px',
                    borderRadius: 11,
                    background: 'transparent',
                    color: TOKENS.inkSoft,
                    fontFamily: TOKENS.fontText, fontSize: 13, fontWeight: 600, letterSpacing: '-0.005em',
                  }}>Paste SMILES...</button>
                </div>

                {/* File-type hints */}
                <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                  {['.csv', '.txt', '.smi'].map((e, i) => (
                    <span key={i} style={{
                      padding: '3px 10px',
                      background: 'rgba(255,255,255,0.65)',
                      borderRadius: 6,
                      fontFamily: TOKENS.fontMono, fontSize: 11, color: TOKENS.inkSoft, fontWeight: 700,
                      boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
                    }}>{e}</span>
                  ))}
                </div>
              </div>

              {/* Run Screening footer */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <button onClick={() => file && mut.mutate()} disabled={!file || mut.isPending} style={{
                  appearance: 'none', border: 'none', cursor: 'pointer',
                  flex: 1,
                  height: 56, padding: '0 24px',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 10,
                  borderRadius: 16,
                  background: !file || mut.isPending ? 'rgba(15,18,28,0.18)' : `linear-gradient(180deg, oklch(70% 0.13 155), oklch(58% 0.13 155))`,
                  color: '#fff',
                  fontFamily: TOKENS.fontText, fontSize: 15, fontWeight: 600, letterSpacing: '-0.005em',
                  boxShadow: '0 1px 0 rgba(255,255,255,0.35) inset, 0 0 0 1px oklch(48% 0.13 155 / 0.5), 0 6px 14px -4px oklch(50% 0.13 155 / 0.45)',
                }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 12h4l3-8 4 16 3-8h4"/>
                  </svg>
                  {mut.isPending ? 'Running...' : 'Run Screening'}
                </button>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '0 18px',
                  height: 56,
                  background: 'rgba(255,255,255,0.55)',
                  borderRadius: 16,
                  boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
                }}>
                  <span style={{ color: TOKENS.inkMuted, display: 'flex' }}><Icon name="info" size={15}/></span>
                  <span style={{ fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted, fontWeight: 500, maxWidth: 220, lineHeight: 1.4 }}>
                    {mut.error ? String(mut.error.message ?? mut.error) : <>Predictions write to <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.inkSoft }}>screening_results.csv</span></>}
                  </span>
                </div>
              </div>
              {file && !mut.isPending && (
                <button onClick={() => selectFile(null)} style={{
                  appearance: 'none', border: 'none', cursor: 'pointer', alignSelf: 'flex-start',
                  padding: '8px 14px',
                  borderRadius: 11,
                  background: 'rgba(255,255,255,0.6)',
                  color: TOKENS.inkSoft,
                  fontFamily: TOKENS.fontText, fontSize: 12.5, fontWeight: 700,
                  boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
                }}>Clear input</button>
              )}
            </Glass>

            {/* RIGHT: results */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <Glass tone="A" radius={18} padding={18} style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 520 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Label>Screening results</Label>
                  <button onClick={downloadCsv} disabled={!results.length} style={{
                    appearance: 'none', border: 'none', cursor: results.length ? 'pointer' : 'default',
                    fontFamily: TOKENS.fontText, fontSize: 11, color: results.length ? TOKENS.accentInk : TOKENS.inkFaint,
                    fontWeight: 700, background: 'transparent',
                  }}>Export CSV</button>
                </div>
                {hasResults ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 2 }}>
                    <SchemaRow k="Total" v={String(results.length)} mono/>
                    <SchemaRow k="Valid" v={String(validResults.length)} mono/>
                    <SchemaRow k="Active" v={String(activeResults.length)} mono/>
                  </div>
                ) : (
                  <div style={{
                    minHeight: 132,
                    display: 'grid',
                    placeItems: 'center',
                    textAlign: 'center',
                    padding: '18px 14px',
                    background: 'rgba(255,255,255,0.45)',
                    borderRadius: 12,
                    boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
                  }}>
                    <div>
                      <div style={{ fontFamily: TOKENS.fontText, fontSize: 13, color: TOKENS.ink, fontWeight: 700 }}>No screening results yet</div>
                      <div style={{ marginTop: 6, fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted, lineHeight: 1.45 }}>
                        Upload or paste SMILES, then run the analysis to populate this panel.
                      </div>
                    </div>
                  </div>
                )}
                {hasResults && <div style={{ display: 'flex', flexDirection: 'column', gap: 10, overflowY: 'auto', paddingRight: 4 }}>
                {resultRows.map((r, i) => (
                  <div key={r.key} onMouseEnter={() => setHovered(r)} onMouseLeave={() => setHovered(null)} style={{
                    position: 'relative',
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '8px 10px',
                    background: 'rgba(255,255,255,0.5)',
                    borderRadius: 10,
                    boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.05)',
                    cursor: r.hit === 'Invalid' ? 'default' : 'help',
                  }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: 7,
                      background: 'oklch(66% 0.115 155 / 0.14)',
                      color: TOKENS.accentInk,
                      display: 'grid', placeItems: 'center',
                    }}>
                      <Icon name="file" size={13}/>
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontFamily: TOKENS.fontMono, fontSize: 12, color: TOKENS.ink, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.name}</div>
                      <div style={{ fontFamily: TOKENS.fontText, fontSize: 10.5, color: TOKENS.inkMuted, marginTop: 1 }}>
                        P(active) {r.n} | {r.when}
                      </div>
                    </div>
                    <span style={{
                      padding: '3px 9px',
                      background: r.tone === 'active' ? 'oklch(66% 0.115 155 / 0.16)' : r.tone === 'inactive' ? 'oklch(70% 0.08 245 / 0.18)' : 'oklch(70% 0.10 28 / 0.18)',
                      color: r.tone === 'active' ? TOKENS.accentInk : r.tone === 'inactive' ? 'oklch(38% 0.10 245)' : 'oklch(48% 0.12 28)',
                      borderRadius: 999,
                      fontFamily: TOKENS.fontMono, fontSize: 11, fontWeight: 700,
                    }}>{r.hit}</span>
                    {hovered?.key === r.key && r.hit !== 'Invalid' && (
                      <div style={{
                        position: 'absolute',
                        right: 8,
                        bottom: 'calc(100% + 8px)',
                        width: 230,
                        padding: 10,
                        borderRadius: 14,
                        background: 'rgba(255,255,255,0.96)',
                        boxShadow: TOKENS.shadowFloat,
                        zIndex: 20,
                        pointerEvents: 'none',
                      }}>
                        <img src={moleculeImageUrl(r.name, 220, 140)} alt={r.name} style={{ width: '100%', height: 128, objectFit: 'contain', background: '#fff', borderRadius: 10 }}/>
                        <div style={{ marginTop: 7, fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkMuted, overflowWrap: 'anywhere' }}>{r.name}</div>
                      </div>
                    )}
                  </div>
                ))}
                </div>}
              </Glass>
            </div>
          </div>
        </div>
      </div>
      </MeshBackground>
    </div>
  );
};

export default ScreeningPage;




