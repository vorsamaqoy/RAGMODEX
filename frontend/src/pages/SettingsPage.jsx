import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { TOKENS, MeshBackground, Glass, Label, Caption, Icon, Tab, ButtonPrimary, ButtonGhost } from '../glass';
import { clearSavedSession, getLlmCatalog, getModelStatus, pullLocalModel, saveSession, setLlmConfig, uploadModel, uploadTestData, uploadTrainingData } from '../lib/api';
import { useAppStore } from '../store';
import { GlassLlmModelSelect } from '../components/GlassLlmModelSelect';
import { GlassSettingsShortcut } from '../components/GlassSettingsShortcut';

/* RAGMODEX Glass - Settings page artboard */

const SidebarItem = ({ icon, label, active }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 12,
    padding: '9px 12px',
    borderRadius: 12,
    background: active ? 'rgba(255,255,255,0.7)' : 'transparent',
    boxShadow: active ? '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.05), 0 4px 12px -6px rgba(15,18,28,0.10)' : 'none',
    color: active ? TOKENS.ink : TOKENS.inkSoft,
    fontFamily: TOKENS.fontText,
    fontSize: 13.5,
    fontWeight: active ? 600 : 500,
    letterSpacing: '-0.005em',
    cursor: 'pointer',
  }}>
    <span style={{ color: active ? TOKENS.accent : TOKENS.inkMuted, display: 'flex' }}>
      <Icon name={icon} size={17} />
    </span>
    {label}
  </div>
);

const Sidebar = () => (
  <div data-glass-sidebar style={{
    width: 230, flex: '0 0 230px',
    padding: 14,
    display: 'flex', flexDirection: 'column', gap: 4,
  }}>
    {/* Brand */}
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

    <SidebarItem icon="chat" label="Chat"/>
    <SidebarItem icon="flask" label="Prediction"/>
    <SidebarItem icon="layers" label="Design"/>
    <SidebarItem icon="search" label="Screening"/>
    <SidebarItem icon="chart" label="Evaluation"/>
    <SidebarItem icon="sparkle" label="Visualizer"/>

    <div style={{ flex: 1 }}/>

    <GlassSettingsShortcut/>
  </div>
);


const TopBar = () => (
  <div style={{
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '14px 24px 14px 12px',
  }}>
    {/* Breadcrumb */}
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: TOKENS.fontText, fontSize: 13.5, color: TOKENS.inkMuted }}>
      <span>RAGMODEX</span>
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={14}/></span>
      <span style={{ color: TOKENS.ink, fontWeight: 600 }}>Settings</span>
    </div>

    {/* Tab switcher */}
    <Glass tone="B" radius={14} padding={4} style={{ display: 'flex', gap: 2 }}>
      <Tab icon="cpu" label="Model" active dot/>
      <Tab icon="db" label="Dataset"/>
      <GlassLlmModelSelect/>
    </Glass>

    {/* Right meta */}
  </div>
);

/* ---------- Status chips row ---------- */
const StatusChip = ({ icon, label, value, state }) => {
  const ok = state === 'ok';
  const empty = state === 'empty';
  return (
    <div style={{
      flex: 1, display: 'flex', alignItems: 'center', gap: 14,
      padding: '14px 16px',
      background: ok ? 'linear-gradient(180deg, oklch(96% 0.04 155 / 0.85), oklch(94% 0.04 155 / 0.7))' : TOKENS.glassB,
      backdropFilter: 'blur(40px) saturate(180%)',
      WebkitBackdropFilter: 'blur(40px) saturate(180%)',
      borderRadius: 18,
      boxShadow: ok
        ? '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(66% 0.115 155 / 0.18), 0 6px 16px -8px oklch(60% 0.13 155 / 0.25)'
        : TOKENS.shadowCard,
    }}>
      <div style={{
        width: 38, height: 38, borderRadius: 11,
        background: ok ? 'oklch(66% 0.115 155 / 0.14)' : 'rgba(15,18,28,0.045)',
        color: ok ? TOKENS.accentInk : TOKENS.inkFaint,
        display: 'grid', placeItems: 'center',
        flex: '0 0 38px',
      }}>
        <Icon name={icon} size={18}/>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          fontFamily: TOKENS.fontText, fontSize: 13.5, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.005em',
        }}>
          {label}
          {ok && <span style={{ color: TOKENS.accent, display: 'flex' }}><Icon name="checkCircle" size={14}/></span>}
          {empty && <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="xCircle" size={14}/></span>}
        </div>
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkMuted, marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {value}
        </div>
      </div>
    </div>
  );
};

/* ---------- Form atoms ---------- */
const Field = ({ label, hint, children }) => (
  <div>
    <Label style={{ marginBottom: 8 }}>{label}</Label>
    {children}
    {hint && <Caption style={{ marginTop: 6, fontSize: 12 }}>{hint}</Caption>}
  </div>
);

const Input = ({ value, mono, suffix }) => (
  <div style={{
    display: 'flex', alignItems: 'center',
    height: 40, padding: '0 14px',
    background: 'rgba(255,255,255,0.55)',
    backdropFilter: 'blur(20px) saturate(160%)',
    borderRadius: 12,
    boxShadow: TOKENS.shadowInput,
    fontFamily: mono ? TOKENS.fontMono : TOKENS.fontText,
    fontSize: 14,
    color: TOKENS.ink,
    fontWeight: 500,
    letterSpacing: mono ? 0 : '-0.005em',
  }}>
    <span style={{ flex: 1 }}>{value}</span>
    {suffix && <span style={{ color: TOKENS.inkFaint, fontSize: 12, fontFamily: TOKENS.fontText }}>{suffix}</span>}
  </div>
);

const Select = ({ value, badge, options = [], onChange, compact = false }) => {
  const [open, setOpen] = useState(false);
  const selected = options.find(option => (option.value ?? option) === value);
  const selectedLabel = selected?.label ?? selected ?? value;
  return (
    <div style={{ position: 'relative', zIndex: open ? 50 : 1 }}>
      <button
        type="button"
        onClick={event => {
          event.stopPropagation();
          setOpen(current => !current);
        }}
        style={{
          width: '100%',
          minWidth: compact ? 220 : 0,
          height: compact ? 34 : 40,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: compact ? '0 10px 0 12px' : '0 10px 0 14px',
          border: 'none',
          borderRadius: compact ? 10 : 12,
          background: compact ? 'rgba(255,255,255,0.65)' : 'rgba(255,255,255,0.55)',
          backdropFilter: 'blur(20px) saturate(160%)',
          WebkitBackdropFilter: 'blur(20px) saturate(160%)',
          boxShadow: compact ? '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px rgba(15,18,28,0.05)' : TOKENS.shadowInput,
          cursor: 'pointer',
          color: TOKENS.ink,
        }}
      >
        {badge && (
          <span style={{
            height: 22, padding: '0 8px', display: 'inline-flex', alignItems: 'center',
            borderRadius: 6, background: 'oklch(66% 0.115 155 / 0.12)',
            color: TOKENS.accentInk, fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase',
          }}>{badge}</span>
        )}
        <span style={{
          flex: 1,
          minWidth: 0,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          textAlign: 'left',
          fontFamily: TOKENS.fontText,
          fontSize: compact ? 12.5 : 14,
          fontWeight: compact ? 600 : 500,
          color: TOKENS.ink,
          letterSpacing: '-0.005em',
        }}>{selectedLabel}</span>
        <span style={{
          width: 26, height: 26, display: 'grid', placeItems: 'center',
          borderRadius: 7, color: TOKENS.inkMuted,
        }}><Icon name="chevDown" size={15}/></span>
      </button>
      {open && (
        <div
          onClick={event => event.stopPropagation()}
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: compact ? 40 : 46,
            maxHeight: 260,
            overflowY: 'auto',
            padding: 6,
            borderRadius: 14,
            background: 'rgba(255,255,255,0.86)',
            backdropFilter: 'blur(26px) saturate(180%)',
            WebkitBackdropFilter: 'blur(26px) saturate(180%)',
            boxShadow: '0 18px 48px rgba(15,18,28,0.16), 0 0 0 1px rgba(15,18,28,0.08), 0 1px 0 rgba(255,255,255,0.9) inset',
          }}
        >
          {options.map(option => {
            const optionValue = option.value ?? option;
            const optionLabel = option.label ?? option;
            const active = optionValue === value;
            return (
              <button
                key={optionValue}
                type="button"
                onClick={() => {
                  onChange?.(optionValue);
                  setOpen(false);
                }}
                style={{
                  width: '100%',
                  minHeight: 34,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '7px 10px',
                  border: 'none',
                  borderRadius: 10,
                  background: active ? 'oklch(66% 0.115 155 / 0.13)' : 'transparent',
                  color: active ? TOKENS.accentInk : TOKENS.inkSoft,
                  cursor: 'pointer',
                  fontFamily: TOKENS.fontText,
                  fontSize: 12.5,
                  fontWeight: active ? 700 : 600,
                  textAlign: 'left',
                }}
              >
                <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{optionLabel}</span>
                {active && <Icon name="check" size={14}/>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

const Slider = ({ value, max = 1, min = 0, onChange }) => {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div style={{ paddingTop: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, fontWeight: 500 }}>Lower = deterministic - Higher = creative</div>
        <div style={{
          padding: '2px 9px', borderRadius: 7, background: '#fff',
          fontFamily: TOKENS.fontMono, fontSize: 12.5, color: TOKENS.ink, fontWeight: 600,
          boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.06)',
        }}>{value.toFixed(2)}</div>
      </div>
      <div style={{ position: 'relative', height: 6 }}>
        <input
          aria-label="Temperature"
          type="range"
          min={min}
          max={max}
          step={0.05}
          value={value}
          onChange={event => onChange?.(Number(event.target.value))}
          style={{ position: 'absolute', inset: -8, zIndex: 3, opacity: 0, cursor: 'pointer' }}
        />
        <div style={{
          position: 'absolute', inset: 0,
          background: 'rgba(15,18,28,0.08)', borderRadius: 999,
        }}/>
        <div style={{
          position: 'absolute', left: 0, top: 0, bottom: 0, width: `${pct}%`,
          background: `linear-gradient(90deg, ${TOKENS.accent}, oklch(74% 0.13 195))`,
          borderRadius: 999,
        }}/>
        <div style={{
          position: 'absolute', left: `calc(${pct}% - 9px)`, top: -6,
          width: 18, height: 18, borderRadius: 999, background: '#fff',
          boxShadow: '0 0 0 1px rgba(15,18,28,0.10), 0 4px 10px -2px rgba(15,18,28,0.20)',
        }}/>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkFaint }}>
        <span>0.00</span><span>0.50</span><span>1.00</span>
      </div>
    </div>
  );
};


/* ---------- File rows ---------- */
const FileRow = ({ name, sub, state = 'ok' }) => {
  const ok = state === 'ok';
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 12px 10px 10px',
      background: ok ? 'oklch(96% 0.03 155 / 0.7)' : 'rgba(255,255,255,0.45)',
      borderRadius: 12,
      boxShadow: ok ? '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px oklch(66% 0.115 155 / 0.18)' : '0 1px 0 rgba(255,255,255,0.7) inset, 0 0 0 1px rgba(15,18,28,0.05)',
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: 9,
        display: 'grid', placeItems: 'center',
        background: ok ? 'oklch(66% 0.115 155 / 0.16)' : 'rgba(15,18,28,0.05)',
        color: ok ? TOKENS.accentInk : TOKENS.inkMuted,
      }}>
        <Icon name={ok ? 'check' : 'upload'} size={16}/>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 13.5, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.005em' }}>{name}</div>
        {sub && <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted, marginTop: 1 }}>{sub}</div>}
      </div>
      {ok ? (
        <button type="button" onClick={() => window.alert('To replace this file, choose a new one and upload again.')} style={{
          appearance: 'none', border: 'none', cursor: 'pointer',
          width: 26, height: 26, borderRadius: 8,
          background: 'transparent',
          color: TOKENS.inkFaint,
          display: 'grid', placeItems: 'center',
        }}><Icon name="x" size={15}/></button>
      ) : (
        <span style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkFaint, fontStyle: 'italic' }}>No file</span>
      )}
    </div>
  );
};

const ChooseFile = ({ label = 'Choose CSV file...' }) => (
  <div style={{
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '10px 10px 10px 12px',
    background: 'rgba(255,255,255,0.35)',
    border: '1px dashed rgba(15,18,28,0.18)',
    borderRadius: 12,
  }}>
    <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="upload" size={15}/></span>
    <span style={{ flex: 1, fontFamily: TOKENS.fontText, fontSize: 13, color: TOKENS.inkMuted, fontWeight: 500 }}>{label}</span>
    <span style={{
      padding: '4px 10px', borderRadius: 8, background: '#fff',
      fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkSoft, fontWeight: 600,
      boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
    }}>Browse</span>
  </div>
);

/* ---------- Section header ---------- */
const SectionHeader = ({ icon, eyebrow, title, sub }) => (
  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginBottom: 18 }}>
    <div style={{
      width: 44, height: 44, borderRadius: 13,
      background: 'linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.55))',
      display: 'grid', placeItems: 'center',
      color: TOKENS.accent,
      boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.06), 0 6px 14px -8px rgba(15,18,28,0.15)',
    }}>
      <Icon name={icon} size={20}/>
    </div>
    <div style={{ flex: 1, paddingTop: 2 }}>
      <Label style={{ marginBottom: 4 }}>{eyebrow}</Label>
      <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.015em' }}>{title}</div>
      {sub && <Caption style={{ marginTop: 3 }}>{sub}</Caption>}
    </div>
  </div>
);

/* ---------- The page ---------- */
const SettingsPage = () => {
  const setModelStatus = useAppStore(s => s.setModelStatus);
  const setLlmStatus = useAppStore(s => s.setLlmStatus);
  const modelInputRef = useRef(null);
  const trainingInputRef = useRef(null);
  const testInputRef = useRef(null);
  const [modelFile, setModelFile] = useState(null);
  const [trainingFile, setTrainingFile] = useState(null);
  const [testFile, setTestFile] = useState(null);
  const [provider, setProvider] = useState('groq');
  const [model, setModel] = useState('llama-3.3-70b-versatile');
  const [temperature, setTemperature] = useState(0.3);
  const [apiKey, setApiKey] = useState('');
  const [persistApiKey, setPersistApiKey] = useState(false);
  const [pullModelName, setPullModelName] = useState('qwen3:4b');
  const [lockedKeys, setLockedKeys] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('ragmodex_locked_llm_keys') ?? '{}');
    } catch {
      return {};
    }
  });
  const [localEndpoint, setLocalEndpoint] = useState('http://127.0.0.1:11434');
  const statusQ = useQuery({ queryKey: ['model-status'], queryFn: getModelStatus, refetchInterval: 5000 });
  const catalogQ = useQuery({ queryKey: ['llm-catalog'], queryFn: getLlmCatalog, refetchInterval: 15000 });

  useEffect(() => {
    if (!statusQ.data) return;
    setModelStatus({
      modelLoaded: !!statusQ.data.model_loaded,
      trainingData: !!statusQ.data.training_data,
      modelName: String(statusQ.data.model_name ?? ''),
      nMolecules: Number(statusQ.data.n_molecules ?? 0),
    });
    if (statusQ.data.llm_provider) setProvider(statusQ.data.llm_provider);
    if (statusQ.data.llm_model) setModel(statusQ.data.llm_model);
    if (typeof statusQ.data.temperature === 'number') setTemperature(statusQ.data.temperature);
  }, [setModelStatus, statusQ.data]);

  useEffect(() => {
    if (!catalogQ.data) return;
    setProvider(catalogQ.data.provider);
    setModel(catalogQ.data.model);
    setTemperature(catalogQ.data.temperature);
    setLocalEndpoint(catalogQ.data.local_endpoint);
  }, [catalogQ.data]);

  useEffect(() => {
    try {
      localStorage.setItem('ragmodex_locked_llm_keys', JSON.stringify(lockedKeys));
    } catch {}
  }, [lockedKeys]);

  const modelMut = useMutation({
    mutationFn: () => uploadModel(modelFile),
    onSuccess: async () => {
      toast.success('Model uploaded');
      await statusQ.refetch();
    },
    onError: err => toast.error(String(err.message ?? err)),
  });
  const trainingMut = useMutation({
    mutationFn: () => uploadTrainingData(trainingFile, 'smiles', 'label', 3, 2048),
    onSuccess: async data => {
      toast.success(`${data.n_molecules} training molecules loaded`);
      await statusQ.refetch();
    },
    onError: err => toast.error(String(err.message ?? err)),
  });
  const testMut = useMutation({
    mutationFn: () => uploadTestData(testFile, 'smiles', 'label', 3, 2048),
    onSuccess: async data => {
      toast.success(`${data.n_molecules} test molecules loaded`);
      await statusQ.refetch();
    },
    onError: err => toast.error(String(err.message ?? err)),
  });
  const llmMut = useMutation({
    mutationFn: () => setLlmConfig(provider, model, temperature, {
      apiKey: lockedKeys[provider] ? undefined : apiKey,
      persistApiKey,
      localEndpoint,
    }),
    onSuccess: data => {
      setLlmStatus({ provider: data.provider, model: data.model, temperature });
      if (apiKey && persistApiKey) {
        setLockedKeys(current => ({ ...current, [provider]: true }));
      }
      setApiKey('');
      catalogQ.refetch();
      toast.success('LLM configuration saved');
    },
    onError: err => toast.error(String(err.message ?? err)),
  });
  const pullMut = useMutation({
    mutationFn: () => pullLocalModel(pullModelName, localEndpoint),
    onSuccess: async data => {
      toast.success(`${data.model} downloaded locally`);
      await catalogQ.refetch();
      setProvider('local');
      setModel(data.model);
    },
    onError: err => toast.error(String(err.message ?? err)),
  });
  const saveSessionMut = useMutation({
    mutationFn: saveSession,
    onSuccess: data => {
      toast.success(`Session saved${data.n_molecules ? ` with ${data.n_molecules} molecules` : ''}`);
    },
    onError: err => toast.error(String(err.message ?? err)),
  });
  const clearSessionMut = useMutation({
    mutationFn: clearSavedSession,
    onSuccess: () => toast.success('Saved session removed'),
    onError: err => toast.error(String(err.message ?? err)),
  });
  const status = statusQ.data;
  const providers = catalogQ.data?.providers?.length
    ? catalogQ.data.providers
    : [
      { name: 'groq', requires_key: true, key_configured: false, models: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'qwen/qwen3-32b'] },
      { name: 'openai', requires_key: true, key_configured: false, models: ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'] },
      { name: 'anthropic', requires_key: true, key_configured: false, models: ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'] },
      { name: 'local', requires_key: false, key_configured: true, models: ['qwen3:4b', 'qwen3:8b', 'llama3.2:3b'] },
    ];
  const selectedProvider = providers.find(item => item.name === provider) ?? providers[0];
  const providerModels = selectedProvider?.models?.length ? selectedProvider.models : [model];
  const keyLocked = !!lockedKeys[provider];
  const setProviderAndDefaultModel = nextProvider => {
    const next = providers.find(item => item.name === nextProvider);
    setProvider(nextProvider);
    setModel(next?.models?.[0] ?? '');
    setApiKey('');
  };
  return (
  <div style={{
    width: 1440, height: 1024,
    position: 'relative',
    fontFamily: TOKENS.fontText,
    color: TOKENS.ink,
  }}>
    <input ref={modelInputRef} type="file" accept=".pkl,.joblib" style={{ display: 'none' }} onClick={event => event.stopPropagation()} onChange={event => setModelFile(event.target.files?.[0] ?? null)} />
    <input ref={trainingInputRef} type="file" accept=".csv" style={{ display: 'none' }} onClick={event => event.stopPropagation()} onChange={event => setTrainingFile(event.target.files?.[0] ?? null)} />
    <input ref={testInputRef} type="file" accept=".csv" style={{ display: 'none' }} onClick={event => event.stopPropagation()} onChange={event => setTestFile(event.target.files?.[0] ?? null)} />
    <MeshBackground>
      <div style={{ display: 'flex', height: '100%' }}>
        <Sidebar/>

        {/* Main */}
        <div data-glass-main style={{ flex: 1, height: '100%', overflowY: 'auto', padding: '8px 20px 32px 4px', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          {/* Floating top bar */}
          <Glass tone="A" radius={20} padding={0} style={{ marginBottom: 22 }}>
            <TopBar/>
          </Glass>

          {/* Page header */}
          <div style={{ padding: '4px 6px 22px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
              <div>
                <Label style={{ marginBottom: 12, color: TOKENS.accent }}>WORKSPACE - MODEL</Label>
                <h1 style={{
                  margin: 0,
                  fontFamily: TOKENS.fontDisplay,
                  fontSize: 56, fontWeight: 700,
                  letterSpacing: '-0.035em', lineHeight: 1,
                  color: TOKENS.ink,
                }}>Settings</h1>
                <div style={{ marginTop: 14, fontFamily: TOKENS.fontText, fontSize: 15, color: TOKENS.inkMuted, maxWidth: 540, lineHeight: 1.5 }}>
                  Upload the model, attach training and test datasets, and configure the language model that drives responses.
                </div>
              </div>
              <div />
            </div>
          </div>

          {/* Status chips */}
          <div style={{ display: 'flex', gap: 14, marginBottom: 26 }}>
            <StatusChip
              icon="cpu"
              label="Model"
              value={modelFile?.name ?? status?.model_name ?? 'Awaiting upload'}
              state={status?.model_loaded || modelFile ? 'ok' : 'empty'}
            />
            <StatusChip
              icon="db"
              label="Training data"
              value={status?.training_data ? `${status.n_molecules ?? 0} molecules` : trainingFile?.name ?? 'Awaiting upload'}
              state={status?.training_data || trainingFile ? 'ok' : 'empty'}
            />
            <StatusChip
              icon="file"
              label="Test data"
              value={status?.test_data ? `${status.n_test ?? 0} molecules` : testFile?.name ?? 'Optional'}
              state={status?.test_data || testFile ? 'ok' : 'empty'}
            />
            <StatusChip
              icon="sliders"
              label="Fingerprint"
              value={`Morgan r${status?.fp_radius ?? 3} - ${status?.fp_nbits ?? 2048} bits`}
              state="ok"
            />
          </div>

          {/* Two columns */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.15fr 1fr', gap: 22, flex: 1, minHeight: 0 }}>
            {/* LEFT: Assets */}
            <Glass tone="A" radius={26} padding={28} style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
              <SectionHeader
                icon="layers"
                eyebrow="ASSETS"
                title="Model and datasets"
                sub="Drop the trained classifier and the CSV files used for training and evaluation."
              />

              {/* Upload model */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <div>
                    <div style={{ fontFamily: TOKENS.fontText, fontSize: 14, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.005em' }}>Upload model</div>
                    <Caption style={{ marginTop: 2, fontSize: 12 }}>Scikit-learn classifier saved with pickle or joblib (.pkl / .joblib)</Caption>
                  </div>
                  <ButtonGhost
                    icon="upload"
                    onClick={() => {
                      if (!modelFile) {
                        modelInputRef.current?.click();
                        return;
                      }
                      modelMut.mutate();
                    }}
                    disabled={modelMut.isPending}
                  >
                    {modelMut.isPending ? 'Uploading...' : modelFile ? 'Upload' : 'Choose file'}
                  </ButtonGhost>
                </div>
                <FileRow
                  name={modelFile?.name ?? status?.model_name ?? 'No model selected'}
                  sub={modelMut.isPending ? 'Uploading...' : status?.model_loaded ? 'Uploaded' : modelFile ? 'Ready to upload' : 'Select a .pkl or .joblib file'}
                  state={status?.model_loaded || modelFile ? 'ok' : 'empty'}
                />
              </div>

              {/* Fingerprint params */}
              <div>
                <div style={{ marginBottom: 12 }}>
                  <div style={{ fontFamily: TOKENS.fontText, fontSize: 14, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.005em' }}>Fingerprint parameters</div>
                  <Caption style={{ marginTop: 2, fontSize: 12 }}>Used when building training and test fingerprints. Keep aligned with the model's feature count.</Caption>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <Field label="Morgan radius">
                    <Input value="3" mono suffix="bonds"/>
                  </Field>
                  <Field label="Vector length">
                    <Input value="2048" mono suffix="bits"/>
                  </Field>
                </div>
              </div>

              {/* Training + Test data */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <Label style={{ marginBottom: 8 }}>Training data</Label>
                  <Caption style={{ marginBottom: 10, fontSize: 12 }}>CSV with columns <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.inkSoft }}>smiles</span> and <span style={{ fontFamily: TOKENS.fontMono, color: TOKENS.inkSoft }}>label</span> (0/1)</Caption>
                  <div onClick={() => trainingInputRef.current?.click()} style={{ cursor: 'pointer' }}>
                    <ChooseFile label={trainingFile?.name ?? 'Choose CSV file...'} />
                  </div>
                  <div style={{ marginTop: 10 }}>
                    <ButtonGhost icon="upload" onClick={() => trainingFile && trainingMut.mutate()} disabled={!trainingFile || trainingMut.isPending}>
                      {trainingMut.isPending ? 'Uploading...' : 'Upload training data'}
                    </ButtonGhost>
                  </div>
                </div>
                <div>
                  <Label style={{ marginBottom: 8 }}>Test data <span style={{ color: TOKENS.inkFaint, fontWeight: 500, textTransform: 'none', letterSpacing: 0 }}>- optional</span></Label>
                  <Caption style={{ marginBottom: 10, fontSize: 12 }}>Optional CSV used for evaluation metrics and visualizations.</Caption>
                  <div onClick={() => testInputRef.current?.click()} style={{ cursor: 'pointer' }}>
                    <ChooseFile label={testFile?.name ?? 'Choose CSV file...'} />
                  </div>
                  <div style={{ marginTop: 10 }}>
                    <ButtonGhost icon="upload" onClick={() => testFile && testMut.mutate()} disabled={!testFile || testMut.isPending}>
                      {testMut.isPending ? 'Uploading...' : 'Upload test data'}
                    </ButtonGhost>
                  </div>
                </div>
              </div>
            </Glass>

            {/* RIGHT: LLM */}
            <Glass tone="A" radius={26} padding={28} style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
              <SectionHeader
                icon="sparkle"
                eyebrow="LLM"
                title="Response engine"
                sub="Choose provider, model and response variability for generated answers."
              />

              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <Field label="Provider">
                  <Select
                    value={provider}
                    badge={selectedProvider?.requires_key ? 'API' : 'LOCAL'}
                    onChange={setProviderAndDefaultModel}
                    options={providers.map(item => ({
                      value: item.name,
                      label: `${item.name}${item.requires_key && !item.key_configured ? ' - key needed' : ''}`,
                    }))}
                  />
                </Field>
                <Field label="Model">
                  <Select
                    value={model}
                    onChange={setModel}
                    options={providerModels}
                  />
                </Field>
                {provider === 'local' && (
                  <Field label="Local endpoint" hint="Ollama models are refreshed from /api/tags when the local server is running.">
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input
                        type="url"
                        value={localEndpoint}
                        onChange={event => setLocalEndpoint(event.target.value)}
                        style={{
                          flex: 1,
                          height: 40,
                          border: 'none',
                          outline: 'none',
                          borderRadius: 12,
                          padding: '0 14px',
                          background: 'rgba(255,255,255,0.55)',
                          boxShadow: TOKENS.shadowInput,
                          fontFamily: TOKENS.fontText,
                          color: TOKENS.ink,
                        }}
                      />
                      <ButtonGhost icon="sparkle" onClick={() => catalogQ.refetch()} disabled={catalogQ.isFetching}>
                        Refresh
                      </ButtonGhost>
                    </div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                      <input
                        type="text"
                        value={pullModelName}
                        onChange={event => setPullModelName(event.target.value)}
                        placeholder="qwen3:4b"
                        style={{
                          flex: 1,
                          height: 40,
                          border: 'none',
                          outline: 'none',
                          borderRadius: 12,
                          padding: '0 14px',
                          background: 'rgba(255,255,255,0.55)',
                          boxShadow: TOKENS.shadowInput,
                          fontFamily: TOKENS.fontMono,
                          color: TOKENS.ink,
                        }}
                      />
                      <ButtonGhost icon="upload" onClick={() => pullMut.mutate()} disabled={!pullModelName.trim() || pullMut.isPending}>
                        {pullMut.isPending ? 'Downloading...' : 'Download'}
                      </ButtonGhost>
                    </div>
                  </Field>
                )}
                {selectedProvider?.requires_key && (
                  <Field label="API key" hint={selectedProvider.key_configured ? 'Leave empty to keep the current key.' : 'Required for paid or hosted providers.'}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <input
                        type="password"
                        value={keyLocked ? 'locked-key' : apiKey}
                        disabled={keyLocked}
                        onChange={event => setApiKey(event.target.value)}
                        placeholder={`${provider.toUpperCase()} API key`}
                        style={{
                          flex: 1,
                          height: 40,
                          border: 'none',
                          outline: 'none',
                          borderRadius: 12,
                          padding: '0 14px',
                          background: keyLocked ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.55)',
                          boxShadow: TOKENS.shadowInput,
                          fontFamily: TOKENS.fontText,
                          color: TOKENS.ink,
                        }}
                      />
                      {keyLocked && (
                        <ButtonGhost icon="x" onClick={() => setLockedKeys(current => ({ ...current, [provider]: false }))}>
                          Unlock
                        </ButtonGhost>
                      )}
                    </div>
                    <label style={{
                      display: 'flex', alignItems: 'flex-start', gap: 10, marginTop: 10,
                      fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, lineHeight: 1.4,
                    }}>
                      <input
                        type="checkbox"
                        checked={persistApiKey}
                        disabled={keyLocked}
                        onChange={event => setPersistApiKey(event.target.checked)}
                      />
                      <span>Save permanently in the project .env and lock this provider field after saving.</span>
                    </label>
                  </Field>
                )}
                <Field label="Temperature">
                  <Slider value={temperature} onChange={setTemperature}/>
                </Field>
              </div>

              {/* Divider */}
              <div style={{ height: 1, background: TOKENS.glassDivider, margin: '4px 0' }}/>

              <div style={{
                display: 'flex', flexDirection: 'column', gap: 12,
                padding: 16,
                background: 'rgba(255,255,255,0.45)',
                borderRadius: 16,
                boxShadow: '0 1px 0 rgba(255,255,255,0.7) inset, 0 0 0 1px rgba(15,18,28,0.05)',
              }}>
                <div>
                  <Label>Session persistence</Label>
                  <Caption style={{ marginTop: 6 }}>
                    Manual save stores the currently loaded model and datasets for the next app launch.
                  </Caption>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <ButtonPrimary
                    icon="check"
                    full
                    onClick={() => saveSessionMut.mutate()}
                    disabled={saveSessionMut.isPending || (!status?.model_loaded && !status?.training_data && !status?.test_data)}
                  >
                    {saveSessionMut.isPending ? 'Saving...' : 'Save session'}
                  </ButtonPrimary>
                  <ButtonGhost
                    icon="x"
                    onClick={() => clearSessionMut.mutate()}
                    disabled={clearSessionMut.isPending}
                  >
                    {clearSessionMut.isPending ? 'Removing...' : 'Remove saved'}
                  </ButtonGhost>
                </div>
              </div>

              {/* Summary */}
              <div style={{
                display: 'flex', flexDirection: 'column', gap: 10,
                padding: 16,
                background: 'rgba(255,255,255,0.45)',
                borderRadius: 16,
                boxShadow: '0 1px 0 rgba(255,255,255,0.7) inset, 0 0 0 1px rgba(15,18,28,0.05)',
              }}>
                <Label>Active configuration</Label>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: TOKENS.fontText, fontSize: 13 }}>
                  <span style={{ color: TOKENS.inkMuted }}>Provider</span>
                  <span style={{ color: TOKENS.ink, fontWeight: 600 }}>{provider}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: TOKENS.fontText, fontSize: 13 }}>
                  <span style={{ color: TOKENS.inkMuted }}>Model</span>
                  <span style={{ color: TOKENS.ink, fontWeight: 600, fontFamily: TOKENS.fontMono, fontSize: 12.5 }}>{model}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: TOKENS.fontText, fontSize: 13 }}>
                  <span style={{ color: TOKENS.inkMuted }}>Temperature</span>
                  <span style={{ color: TOKENS.ink, fontWeight: 600, fontFamily: TOKENS.fontMono, fontSize: 12.5 }}>{temperature.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: TOKENS.fontText, fontSize: 13 }}>
                  <span style={{ color: TOKENS.inkMuted }}>Estimated latency</span>
                  <span style={{ color: TOKENS.ink, fontWeight: 600 }}>~ 480 ms</span>
                </div>
              </div>

              <div style={{ flex: 1 }}/>
              <ButtonPrimary icon="check" full onClick={() => llmMut.mutate()} disabled={llmMut.isPending}>
                {llmMut.isPending ? 'Saving...' : 'Save configuration'}
              </ButtonPrimary>
            </Glass>
          </div>
        </div>
      </div>
    </MeshBackground>
  </div>
);
};

export default SettingsPage;




