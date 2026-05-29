import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { createPortal } from 'react-dom';
import { TOKENS, MeshBackground, Glass, Label, Icon, Tab, ButtonGhost } from '../glass';
import { chatSimple, comparePredictions, focusPredictionBit, getActiveOnMostAmbiguousBit, getBitDatabaseInfo, getEvaluation, getModelStatus, moleculeHighlightUrl, moleculeImageUrl, predict, streamChat } from '../lib/api';
import { useAppStore } from '../store';
import { GlassLlmModelSelect } from '../components/GlassLlmModelSelect';
import { GlassSettingsShortcut } from '../components/GlassSettingsShortcut';

/* RAGMODEX Glass - Chat page artboard */

const CHAT_STATE_KEY = 'ragmodex_glass_chat_state';

function loadChatState() {
  try {
    const raw = localStorage.getItem(CHAT_STATE_KEY);
    return raw ? JSON.parse(raw) : { recentChats: [], currentChatId: null, messages: [] };
  } catch {
    return { recentChats: [], currentChatId: null, messages: [] };
  }
}

function saveChatState(state) {
  try {
    localStorage.setItem(CHAT_STATE_KEY, JSON.stringify(state));
  } catch {}
}

const ChatSidebar = ({
  recents = [],
  selectedIds = [],
  currentChatId,
  onSelectRecent,
  onToggleRecent,
  onClearSelected,
  onClearAll,
}) => {
  const items = [
    { i: 'chat', l: 'Chat', active: true },
    { i: 'flask', l: 'Prediction' },
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

      {/* Recent chats list */}
      <div style={{ padding: '4px 4px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '0 4px 8px 8px' }}>
          <div style={{
            fontFamily: TOKENS.fontText, fontSize: 10.5, fontWeight: 600, letterSpacing: '0.10em',
            textTransform: 'uppercase', color: TOKENS.inkMuted,
          }}>Recent</div>
          {recents.length > 0 && (
            <button type="button" onClick={onClearAll} style={{
              appearance: 'none', border: 'none', background: 'transparent', cursor: 'pointer',
              fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 600, color: TOKENS.inkMuted,
              padding: '4px 6px', borderRadius: 7,
            }}>
              Clear all
            </button>
          )}
        </div>
        {selectedIds.length > 0 && (
          <button type="button" onClick={onClearSelected} style={{
            appearance: 'none', border: 'none', width: '100%', marginBottom: 7,
            padding: '7px 10px', borderRadius: 9, cursor: 'pointer',
            background: 'rgba(255,255,255,0.62)',
            boxShadow: '0 1px 0 rgba(255,255,255,0.8) inset, 0 0 0 1px rgba(15,18,28,0.06)',
            fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 700, color: TOKENS.accentInk,
          }}>
            Delete selected ({selectedIds.length})
          </button>
        )}
        {recents.map((chat) => (
          <button key={chat.id} type="button" onClick={() => onSelectRecent(chat.id)} style={{
            appearance: 'none', border: 'none', background: 'transparent', width: '100%', textAlign: 'left',
            padding: '7px 10px', borderRadius: 9,
            fontFamily: TOKENS.fontText, fontSize: 12.5, color: chat.id === currentChatId ? TOKENS.ink : TOKENS.inkSoft,
            letterSpacing: '-0.005em',
            display: 'flex', alignItems: 'center', gap: 8,
            cursor: 'pointer',
            background: chat.id === currentChatId ? 'rgba(255,255,255,0.45)' : 'transparent',
          }}>
            <input
              type="checkbox"
              checked={selectedIds.includes(chat.id)}
              onChange={event => {
                event.stopPropagation();
                onToggleRecent(chat.id);
              }}
              onClick={event => event.stopPropagation()}
              aria-label={`Select ${chat.title}`}
              style={{ width: 13, height: 13, margin: 0, flex: '0 0 13px', accentColor: TOKENS.accent }}
            />
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{chat.title}</span>
          </button>
        ))}
      </div>

      <GlassSettingsShortcut/>
    </div>
  );
};

const ChatTopBar = () => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 24px 14px 12px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: TOKENS.fontText, fontSize: 13.5, color: TOKENS.inkMuted }}>
      <span>RAGMODEX</span>
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={14}/></span>
      <span style={{ color: TOKENS.ink, fontWeight: 600 }}>Chat</span>
    </div>

    <Glass tone="B" radius={14} padding={4} style={{ display: 'flex', gap: 2 }}>
      <Tab icon="cpu" label="Model" active dot/>
      <Tab icon="db" label="Dataset" dot/>
      <GlassLlmModelSelect/>
    </Glass>
  </div>
);

/* ---------- Suggestion card ---------- */
const SuggestionCard = ({ icon, title, sub, prompt, onClick }) => (
  <button type="button" onClick={onClick} style={{
    appearance: 'none', border: 'none', textAlign: 'left',
    flex: 1, minWidth: 0,
    padding: 18,
    background: 'rgba(255,255,255,0.55)',
    backdropFilter: 'blur(40px) saturate(180%)',
    borderRadius: 18,
    boxShadow: TOKENS.shadowCard,
    display: 'flex', flexDirection: 'column', gap: 10,
    cursor: 'pointer',
    transition: 'transform .2s ease',
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{
        width: 32, height: 32, borderRadius: 9,
        background: 'oklch(66% 0.115 155 / 0.14)',
        color: TOKENS.accentInk,
        display: 'grid', placeItems: 'center',
      }}>
        <Icon name={icon} size={16}/>
      </div>
      <div style={{ fontFamily: TOKENS.fontText, fontSize: 14, fontWeight: 600, color: TOKENS.ink, letterSpacing: '-0.005em' }}>{title}</div>
      <div style={{ flex: 1 }}/>
      <span style={{ color: TOKENS.inkFaint, display: 'flex' }}><Icon name="chevRight" size={15}/></span>
    </div>
    <div style={{ fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkMuted, lineHeight: 1.45 }}>{sub}</div>
    <div style={{
      marginTop: 4,
      padding: '7px 10px',
      background: 'rgba(15,18,28,0.04)',
      borderRadius: 8,
      fontFamily: TOKENS.fontMono, fontSize: 11, color: TOKENS.inkSoft,
      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
    }}>{prompt}</div>
  </button>
);

/* ---------- Example prompt chip ---------- */
const ExampleChip = ({ children, onClick }) => (
  <button type="button" onClick={onClick} style={{
    appearance: 'none', cursor: 'pointer', border: 'none',
    display: 'inline-flex', alignItems: 'center', gap: 8,
    padding: '8px 14px',
    background: 'rgba(255,255,255,0.55)',
    borderRadius: 999,
    boxShadow: '0 1px 0 rgba(255,255,255,0.85) inset, 0 0 0 1px rgba(15,18,28,0.06)',
    fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkSoft, fontWeight: 500, letterSpacing: '-0.005em',
  }}>
    <span style={{ color: TOKENS.accent, display: 'flex' }}><Icon name="sparkle" size={13}/></span>
    {children}
  </button>
);

const MOLECULE_TOKEN_RE = /(?:["'`](.+?)["'`])|(?:\b(?:[A-Z][a-z]?|c|n|o|s|p|\[[^\]]+\])(?:[A-Za-z0-9@+\-\[\]\(\)=#$:\/\\%.]{2,})\b)/g;
const MOLECULE_MIN_CHARS = 3;
const CANONICAL_SMILES_RE = /canonical\s+SMILES\s*[:=]\s*([^\s;,.]+)/i;

function cleanSmilesToken(value) {
  return (value ?? '').trim().replace(/^[`'"]+|[`'",.;:]+$/g, '');
}

function looksLikeStrongSmiles(value) {
  const token = cleanSmilesToken(value);
  if (token.length < MOLECULE_MIN_CHARS || /\s/.test(token)) return false;
  if (!/^[A-Za-z0-9@+\-\[\]\(\)=#$:\/\\%.]+$/.test(token)) return false;
  if (/^(active|inactive|smiles|model|dataset|prediction|probability|bbb|cyp)$/i.test(token)) return false;
  return /[cnosp]/.test(token) || /[\[\]\(\)=#@0-9]/.test(token);
}

function extractQuerySmiles(text) {
  const patterns = [
    /\b(?:predict|analyze|analyse|interpret|explain|score|evaluate|predici|spiega)\s+["'`]?([^,\n; "'`]+)["'`]?/i,
    /\bfor\s+molecule\s+([^,\n;]+)/i,
    /\bgiven\s+molecule\s+([^,\n;]+)/i,
    /\bSMILES(?:\s+string)?\s*[:=]?\s*([^,\n;]+)/i,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    const candidate = cleanSmilesToken(match?.[1]);
    if (looksLikeStrongSmiles(candidate)) return candidate;
  }
  for (const match of text.matchAll(MOLECULE_TOKEN_RE)) {
    const candidate = cleanSmilesToken(match[1] ?? match[0]);
    if (looksLikeStrongSmiles(candidate)) return candidate;
  }
  return null;
}

function extractQuerySmilesPair(text) {
  const patterns = [
    /\bCompare\s+([^,\n; ]+)\s+and\s+([^,\n; ]+)/i,
    /\bWhich\s+of\s+([^,\n; ]+)\s+and\s+([^,\n; ]+)/i,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    const first = cleanSmilesToken(match?.[1]);
    const second = cleanSmilesToken(match?.[2]);
    if (looksLikeStrongSmiles(first) && looksLikeStrongSmiles(second)) {
      return [first, second];
    }
  }
  return null;
}

function extractBitIndex(text) {
  const match = text.match(/\bECFP\d+\s*(?:bit\s*)?[_-]?\s*(\d{1,5})\b/i)
    ?? text.match(/\bbit\s+(\d{1,5})\b/i);
  return match ? Number(match[1]) : null;
}

function extractMoleculePredictionIntent(text) {
  const lowered = text.toLowerCase();
  if (lowered.includes('strongest negative shap') || lowered.includes('single strongest negative')) {
    return { type: 'strongest-negative' };
  }
  const bitIndex = extractBitIndex(text);
  if (
    bitIndex !== null
    && (
      /\bis\s+ECFP\d+\s+bit\s+\d+\s+ON/i.test(text)
      || lowered.includes('molecule-level substructure')
      || lowered.includes('activates it')
    )
  ) {
    return { type: 'specific-bit', bitIndex };
  }
  return null;
}

function extractBitDatabaseIntent(text, smiles = null) {
  const lowered = text.toLowerCase();
  if (smiles && lowered.includes('active on bit') && lowered.includes('ambiguous')) {
    return { mode: 'active-on-most-ambiguous', smiles };
  }
  if (lowered.includes('highest active ratio') || lowered.includes('highest active association')) {
    return { mode: 'top-active' };
  }
  if (lowered.includes('strongest inactive association') || lowered.includes('highest inactive association')) {
    return { mode: 'top-inactive' };
  }
  const asksBitDb = lowered.includes('loaded training set')
    || lowered.includes('training set')
    || lowered.includes('training-set')
    || lowered.includes('loaded bit database')
    || lowered.includes('bit database')
    || lowered.includes('what does ecfp')
    || lowered.includes('hash to this bit')
    || lowered.includes('appears unambiguous')
    || lowered.includes('reliable chemical interpretation')
    || lowered.includes('universal chemical meaning')
    || lowered.includes('low confidence')
    || lowered.includes('collision confidence')
    || (lowered.includes('interpretation') && lowered.includes('confidence'));
  if (!asksBitDb) return null;
  if (lowered.includes('highest number of unique substructures') || lowered.includes('most ambiguous')) {
    return { mode: 'most-ambiguous' };
  }
  const bitIndex = extractBitIndex(text);
  return bitIndex !== null ? { bitIndex } : null;
}

function extractChartIntent(text) {
  const lowered = text.toLowerCase();
  if (lowered.includes('confusion matrix')) return { type: 'confusion-matrix' };
  if (lowered.includes('roc-auc') || lowered.includes('pr-auc') || lowered.includes('roc auc') || lowered.includes('pr auc')) {
    return { type: 'metric-bars' };
  }
  if (lowered.includes('active and inactive') || lowered.includes('class balance') || lowered.includes('class distribution')) {
    if (lowered.includes('test')) return { type: 'class-balance', split: 'test' };
    return { type: 'class-balance', split: 'training' };
  }
  if (
    (lowered.includes('how many') || lowered.includes('molecules')) &&
    lowered.includes('training') &&
    lowered.includes('test')
  ) {
    return { type: 'dataset-sizes' };
  }
  return null;
}

function extractCanonicalSmiles(text) {
  const candidate = cleanSmilesToken(text.match(CANONICAL_SMILES_RE)?.[1]);
  return looksLikeStrongSmiles(candidate) ? candidate : null;
}

function probabilityTone(value) {
  if (value >= 0.7) return { label: 'High confidence Active', color: 'oklch(60% 0.13 155)', fill: 'linear-gradient(90deg, oklch(70% 0.12 155), oklch(58% 0.13 155))' };
  if (value >= 0.4) return { label: 'Borderline', color: 'oklch(63% 0.14 72)', fill: 'linear-gradient(90deg, oklch(83% 0.13 82), oklch(68% 0.16 70))' };
  return { label: 'Low active probability', color: 'oklch(58% 0.16 28)', fill: 'linear-gradient(90deg, oklch(76% 0.12 30), oklch(60% 0.17 24))' };
}

const formatProb = value => Number.isFinite(value) ? value.toFixed(3) : 'n/a';
const formatSigned = value => `${value >= 0 ? '+' : ''}${Number(value).toFixed(4)}`;

const ProbabilityGauge = ({ value, inactive }) => {
  const tone = probabilityTone(value);
  const pct = Math.max(0, Math.min(100, value * 100));
  const inactiveValue = Number.isFinite(inactive) ? inactive : 1 - value;
  return (
    <div style={{ display: 'grid', gap: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 700, color: TOKENS.inkSoft }}>P(active)</div>
        <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 22, fontWeight: 800, color: tone.color, letterSpacing: 0 }}>{formatProb(value)}</div>
      </div>
      <div style={{
        height: 12,
        borderRadius: 999,
        background: 'rgba(15,18,28,0.08)',
        boxShadow: '0 1px 0 rgba(255,255,255,0.75) inset, 0 0 0 1px rgba(15,18,28,0.06)',
        overflow: 'hidden',
      }}>
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 999, background: tone.fill }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted }}>
        <span>{tone.label}</span>
        <span>P(inactive) {formatProb(inactiveValue)}</span>
      </div>
    </div>
  );
};

const HighlightLocatorTooltip = ({
  anchorRect,
  bit,
  color,
  moleculeSmiles,
  subInfo,
  highlightDirection,
  tooltipBorder,
}) => {
  if (!anchorRect || !subInfo || typeof window === 'undefined' || typeof document === 'undefined') return null;

  const margin = 12;
  const width = Math.min(344, window.innerWidth - margin * 2);
  const estimatedHeight = 282;
  const belowTop = anchorRect.bottom + 10;
  const top = belowTop + estimatedHeight > window.innerHeight - margin
    ? Math.max(margin, anchorRect.top - estimatedHeight - 10)
    : belowTop;
  const left = Math.min(
    window.innerWidth - width - margin,
    Math.max(margin, anchorRect.right - width),
  );

  return createPortal(
    <div style={{
      position: 'fixed',
      left,
      top,
      zIndex: 2147483647,
      width,
      padding: 10,
      borderRadius: 14,
      background: 'rgba(255,255,255,0.98)',
      boxShadow: `0 0 0 1px ${tooltipBorder}, 0 22px 52px -22px rgba(15,18,28,0.55)`,
      pointerEvents: 'none',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 10,
        marginBottom: 7,
        fontFamily: TOKENS.fontText,
        fontSize: 11.5,
        color: TOKENS.inkSoft,
      }}>
        <span style={{ fontWeight: 800, color }}>Located in full molecule</span>
        <span>atom {subInfo.atom_idx} · r{subInfo.radius}</span>
      </div>
      <img
        src={moleculeHighlightUrl(moleculeSmiles, subInfo.atom_idx, subInfo.radius, highlightDirection, 420, 300)}
        alt={`Highlighted ${bit.bit} environment in full molecule`}
        loading="lazy"
        decoding="async"
        style={{
          width: '100%',
          height: 226,
          objectFit: 'contain',
          display: 'block',
          borderRadius: 10,
          background: '#fff',
          boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
        }}
      />
    </div>,
    document.body,
  );
};

const ShapBitRow = ({ bit, maxAbs, moleculeSmiles }) => {
  const [hovered, setHovered] = useState(false);
  const [anchorRect, setAnchorRect] = useState(null);
  const rowRef = useRef(null);
  const shap = Number(bit.shap_value ?? 0);
  const abs = Math.abs(shap);
  const width = maxAbs > 0 ? Math.max(8, Math.min(100, (abs / maxAbs) * 100)) : 8;
  const towardActive = shap >= 0;
  const color = towardActive ? 'oklch(60% 0.13 155)' : 'oklch(58% 0.16 28)';
  const subInfo = bit.molecule_substructures?.[0] ?? null;
  const sub = subInfo?.smiles ?? bit.training_info?.dominant_substructure ?? null;
  const canLocate = moleculeSmiles && subInfo && Number.isFinite(Number(subInfo.atom_idx)) && Number.isFinite(Number(subInfo.radius));
  const highlightDirection = towardActive ? 'active' : 'inactive';
  const tooltipBorder = towardActive ? 'oklch(60% 0.13 155 / 0.42)' : 'oklch(58% 0.16 28 / 0.42)';
  const tooltipTint = towardActive ? 'rgba(9, 128, 72, 0.08)' : 'rgba(190, 42, 28, 0.08)';
  const showLocator = event => {
    if (!canLocate) return;
    setAnchorRect((event.currentTarget ?? rowRef.current).getBoundingClientRect());
    setHovered(true);
  };
  const hideLocator = () => setHovered(false);

  return (
    <div ref={rowRef} style={{
      position: 'relative',
      display: 'grid',
      gridTemplateColumns: '96px minmax(180px, 1fr) 104px',
      gap: 12,
      alignItems: 'center',
      padding: '10px 0',
      borderTop: '1px solid rgba(15,18,28,0.08)',
      whiteSpace: 'normal',
    }}>
      <div>
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 12.5, fontWeight: 800, color: TOKENS.ink }}>{bit.bit}</div>
        <div style={{ marginTop: 3, fontFamily: TOKENS.fontText, fontSize: 11.5, color }}>{towardActive ? 'toward Active' : 'toward Inactive'}</div>
      </div>
      <div style={{ display: 'grid', gap: 5 }}>
        <div style={{ position: 'relative', height: 16, borderRadius: 999, background: 'rgba(15,18,28,0.07)', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: 'rgba(15,18,28,0.24)' }} />
          <div style={{
            position: 'absolute',
            top: 2,
            bottom: 2,
            left: towardActive ? '50%' : `${50 - width / 2}%`,
            width: `${width / 2}%`,
            borderRadius: 999,
            background: color,
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted }}>
          <span>SHAP {formatSigned(shap)}</span>
          <span>{Number(bit.bit_on) ? 'bit on' : 'bit off'}</span>
        </div>
        {sub && (
          <div
            onMouseEnter={showLocator}
            onMouseMove={showLocator}
            onMouseLeave={hideLocator}
            style={{
              display: 'inline-block',
              justifySelf: 'start',
              padding: canLocate ? '2px 5px' : 0,
              marginLeft: canLocate ? -5 : 0,
              borderRadius: 7,
              background: canLocate && hovered ? tooltipTint : 'transparent',
              fontFamily: TOKENS.fontText,
              fontSize: 11.5,
              color: TOKENS.inkSoft,
              overflowWrap: 'anywhere',
              cursor: canLocate ? 'help' : 'default',
            }}
          >
            Substructure: {sub}
          </div>
        )}
      </div>
      {bit.molecule_substructures?.[0]?.smiles ? (
        <div
          onMouseEnter={showLocator}
          onMouseMove={showLocator}
          onMouseLeave={hideLocator}
          style={{ position: 'relative', justifySelf: 'end', cursor: canLocate ? 'help' : 'default' }}
        >
          <img
            src={moleculeImageUrl(bit.molecule_substructures[0].smiles, 132, 82)}
            alt={bit.molecule_substructures[0].smiles}
            loading="lazy"
            decoding="async"
            style={{
              width: 96,
              height: 60,
              objectFit: 'contain',
              display: 'block',
              background: 'rgba(255,255,255,0.86)',
              borderRadius: 9,
              boxShadow: hovered && canLocate
                ? `0 0 0 2px ${tooltipBorder}, 0 10px 22px -16px rgba(15,18,28,0.55)`
                : '0 0 0 1px rgba(15,18,28,0.06)',
            }}
          />
        </div>
      ) : (
        <div style={{
          justifySelf: 'end',
          width: 96,
          height: 60,
          borderRadius: 9,
          background: 'rgba(15,18,28,0.05)',
          display: 'grid',
          placeItems: 'center',
          fontFamily: TOKENS.fontText,
          fontSize: 11,
          color: TOKENS.inkMuted,
        }}>
          no image
        </div>
      )}
      {hovered && canLocate && (
        <HighlightLocatorTooltip
          anchorRect={anchorRect}
          bit={bit}
          color={color}
          moleculeSmiles={moleculeSmiles}
          subInfo={subInfo}
          highlightDirection={highlightDirection}
          tooltipBorder={tooltipBorder}
        />
      )}
    </div>
  );
};

function pickFocusedBits(data, intent) {
  const allBits = data.top_bits ?? [];
  if (intent?.type === 'strongest-negative') {
    const strongest = [...allBits]
      .filter(bit => Number(bit.shap_value) < 0)
      .sort((a, b) => Number(a.shap_value) - Number(b.shap_value))[0];
    return strongest ? [strongest] : [];
  }
  if (intent?.type === 'specific-bit') {
    const exact = allBits.find(bit => Number(bit.bit_index) === Number(intent.bitIndex));
    return exact ? [exact] : [];
  }
  return allBits.slice(0, 3);
}

function predictionBitTitle(intent) {
  if (intent?.type === 'strongest-negative') return 'Strongest negative SHAP bit';
  if (intent?.type === 'specific-bit') return `Requested ECFP6 bit ${intent.bitIndex}`;
  return 'Top SHAP ECFP6 drivers';
}

const InlinePrediction = ({ smiles, intent }) => {
  const focused = !!intent;
  const { data, isLoading, isError } = useQuery({
    queryKey: ['chat-inline-prediction', smiles, intent?.type ?? 'default', intent?.bitIndex ?? null],
    queryFn: () => focused
      ? focusPredictionBit(
        smiles,
        intent.type === 'strongest-negative'
          ? { mode: 'strongest-negative' }
          : { bit_index: intent.bitIndex },
      )
      : predict(smiles, 6),
    enabled: !!smiles,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (!smiles || isError) return null;
  if (isLoading) {
    return (
      <div style={{
        marginBottom: 12,
        padding: 12,
        borderRadius: 14,
        background: 'rgba(255,255,255,0.58)',
        boxShadow: '0 1px 0 rgba(255,255,255,0.78) inset, 0 0 0 1px rgba(15,18,28,0.06)',
        fontFamily: TOKENS.fontText,
        fontSize: 12.5,
        color: TOKENS.inkMuted,
        whiteSpace: 'normal',
      }}>
        Building prediction card...
      </div>
    );
  }
  if (!data) return null;

  const prediction = data.focus_bit ? data.prediction : data;
  const topBits = data.focus_bit ? [data.focus_bit] : pickFocusedBits(prediction, intent);
  const maxAbs = topBits.reduce((acc, bit) => Math.max(acc, Math.abs(Number(bit.shap_value ?? 0))), 0);
  const active = Number(prediction.probability_active ?? 0);
  const tone = probabilityTone(active);

  return (
    <div style={{
      marginBottom: 14,
      padding: 14,
      borderRadius: 16,
      background: 'rgba(255,255,255,0.74)',
      boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.07)',
      whiteSpace: 'normal',
    }}>
      <div style={{ display: 'grid', gridTemplateColumns: '170px minmax(0, 1fr)', gap: 16, alignItems: 'center' }}>
        <div style={{
          padding: 10,
          borderRadius: 13,
          background: 'rgba(255,255,255,0.92)',
          boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
        }}>
          <img
            src={moleculeImageUrl(prediction.canonical_smiles ?? smiles, 280, 190)}
            alt={prediction.canonical_smiles ?? smiles}
            loading="lazy"
            decoding="async"
            style={{ width: '100%', height: 124, objectFit: 'contain', display: 'block' }}
          />
        </div>
        <div style={{ display: 'grid', gap: 12, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <div>
              <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: TOKENS.inkMuted }}>
                Model prediction
              </div>
              <div style={{ marginTop: 3, fontFamily: TOKENS.fontDisplay, fontSize: 24, fontWeight: 800, color: tone.color, letterSpacing: 0 }}>
                {prediction.prediction}
              </div>
            </div>
            <div style={{
              padding: '6px 9px',
              borderRadius: 999,
              background: 'rgba(15,18,28,0.05)',
              color: TOKENS.inkSoft,
              fontFamily: TOKENS.fontText,
              fontSize: 11.5,
              fontWeight: 700,
            }}>
              {prediction.n_on_bits} active ECFP6 bits
            </div>
          </div>
          <ProbabilityGauge value={active} inactive={Number(prediction.probability_inactive)} />
          <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted, overflowWrap: 'anywhere' }}>
            Canonical SMILES: {prediction.canonical_smiles}
          </div>
        </div>
      </div>
      {topBits.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 800, color: TOKENS.inkSoft, marginBottom: 2 }}>
            {predictionBitTitle(intent)}
          </div>
          {topBits.map(bit => (
            <ShapBitRow
              key={bit.bit}
              bit={bit}
              maxAbs={maxAbs}
              moleculeSmiles={prediction.canonical_smiles ?? smiles}
            />
          ))}
        </div>
      )}
      {intent && topBits.length === 0 && (
        <div style={{
          marginTop: 14,
          padding: 10,
          borderRadius: 11,
          background: 'rgba(15,18,28,0.05)',
          fontFamily: TOKENS.fontText,
          fontSize: 12,
          color: TOKENS.inkMuted,
          whiteSpace: 'normal',
        }}>
          The requested bit was not found in the returned SHAP ranking for this molecule.
        </div>
      )}
    </div>
  );
};

const CompareMoleculePanel = ({ label, result, winner }) => {
  const active = Number(result.probability_active ?? 0);
  const tone = probabilityTone(active);
  return (
    <div style={{
      display: 'grid',
      gridTemplateRows: 'auto auto 1fr',
      gap: 10,
      minWidth: 0,
      padding: 11,
      borderRadius: 14,
      background: winner ? 'rgba(9,128,72,0.08)' : 'rgba(255,255,255,0.72)',
      boxShadow: winner
        ? '0 0 0 1px oklch(60% 0.13 155 / 0.28), 0 1px 0 rgba(255,255,255,0.82) inset'
        : '0 0 0 1px rgba(15,18,28,0.06), 0 1px 0 rgba(255,255,255,0.82) inset',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 800, color: TOKENS.ink }}>{label}</div>
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 800, color: winner ? tone.color : TOKENS.inkMuted }}>
          {winner ? 'more active' : result.prediction}
        </div>
      </div>
      <div style={{ borderRadius: 12, background: '#fff', boxShadow: '0 0 0 1px rgba(15,18,28,0.06)' }}>
        <img
          src={moleculeImageUrl(result.canonical_smiles, 280, 180)}
          alt={result.canonical_smiles}
          loading="lazy"
          decoding="async"
          style={{ width: '100%', height: 124, objectFit: 'contain', display: 'block' }}
        />
      </div>
      <div style={{ display: 'grid', gap: 7 }}>
        <ProbabilityGauge value={active} inactive={Number(result.probability_inactive)} />
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted, overflowWrap: 'anywhere' }}>
          {result.canonical_smiles}
        </div>
      </div>
    </div>
  );
};

const ComparisonBitRow = ({ bit, maxAbs, mol1Smiles, mol2Smiles }) => {
  const [hovered, setHovered] = useState(false);
  const [anchorRect, setAnchorRect] = useState(null);
  const shapDiff = Number(bit.shap_diff ?? 0);
  const abs = Math.abs(shapDiff);
  const width = maxAbs > 0 ? Math.max(8, Math.min(100, (abs / maxAbs) * 100)) : 8;
  const favorsMol2 = shapDiff >= 0;
  const color = favorsMol2 ? 'oklch(60% 0.13 155)' : 'oklch(58% 0.16 28)';
  const tooltipBorder = favorsMol2 ? 'oklch(60% 0.13 155 / 0.42)' : 'oklch(58% 0.16 28 / 0.42)';
  const tooltipTint = favorsMol2 ? 'rgba(9, 128, 72, 0.08)' : 'rgba(190, 42, 28, 0.08)';
  const subInfo = bit.mol_subs?.[0] ?? null;
  const sourceSmiles = bit.in_mol1 ? mol1Smiles : mol2Smiles;
  const highlightDirection = favorsMol2 ? 'active' : 'inactive';
  const canLocate = sourceSmiles && subInfo && Number.isFinite(Number(subInfo.atom_idx)) && Number.isFinite(Number(subInfo.radius));
  const showLocator = event => {
    if (!canLocate) return;
    setAnchorRect(event.currentTarget.getBoundingClientRect());
    setHovered(true);
  };
  const hideLocator = () => setHovered(false);

  return (
    <div style={{
      position: 'relative',
      display: 'grid',
      gridTemplateColumns: '96px minmax(180px, 1fr) 104px',
      gap: 12,
      alignItems: 'center',
      padding: '10px 0',
      borderTop: '1px solid rgba(15,18,28,0.08)',
      whiteSpace: 'normal',
    }}>
      <div>
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 12.5, fontWeight: 800, color: TOKENS.ink }}>{bit.bit}</div>
        <div style={{ marginTop: 3, fontFamily: TOKENS.fontText, fontSize: 11.5, color }}>
          favors {favorsMol2 ? 'mol2' : 'mol1'}
        </div>
      </div>
      <div style={{ display: 'grid', gap: 5 }}>
        <div style={{ position: 'relative', height: 16, borderRadius: 999, background: 'rgba(15,18,28,0.07)', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: 'rgba(15,18,28,0.24)' }} />
          <div style={{
            position: 'absolute',
            top: 2,
            bottom: 2,
            left: favorsMol2 ? '50%' : `${50 - width / 2}%`,
            width: `${width / 2}%`,
            borderRadius: 999,
            background: color,
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted }}>
          <span>SHAP diff {formatSigned(shapDiff)}</span>
          <span>{bit.in_mol1 ? 'mol1' : ''}{bit.in_mol1 && bit.in_mol2 ? ' + ' : ''}{bit.in_mol2 ? 'mol2' : ''}</span>
        </div>
        {subInfo?.smiles && (
          <div
            onMouseEnter={showLocator}
            onMouseMove={showLocator}
            onMouseLeave={hideLocator}
            style={{
              display: 'inline-block',
              justifySelf: 'start',
              padding: canLocate ? '2px 5px' : 0,
              marginLeft: canLocate ? -5 : 0,
              borderRadius: 7,
              background: canLocate && hovered ? tooltipTint : 'transparent',
              fontFamily: TOKENS.fontText,
              fontSize: 11.5,
              color: TOKENS.inkSoft,
              overflowWrap: 'anywhere',
              cursor: canLocate ? 'help' : 'default',
            }}
          >
            Substructure: {subInfo.smiles}
          </div>
        )}
      </div>
      {subInfo?.smiles ? (
        <div
          onMouseEnter={showLocator}
          onMouseMove={showLocator}
          onMouseLeave={hideLocator}
          style={{ justifySelf: 'end', cursor: canLocate ? 'help' : 'default' }}
        >
          <img
            src={moleculeImageUrl(subInfo.smiles, 132, 82)}
            alt={subInfo.smiles}
            loading="lazy"
            decoding="async"
            style={{
              width: 96,
              height: 60,
              objectFit: 'contain',
              display: 'block',
              background: 'rgba(255,255,255,0.86)',
              borderRadius: 9,
              boxShadow: hovered && canLocate
                ? `0 0 0 2px ${tooltipBorder}, 0 10px 22px -16px rgba(15,18,28,0.55)`
                : '0 0 0 1px rgba(15,18,28,0.06)',
            }}
          />
        </div>
      ) : (
        <div style={{ justifySelf: 'end', width: 96, height: 60, borderRadius: 9, background: 'rgba(15,18,28,0.05)', display: 'grid', placeItems: 'center', fontFamily: TOKENS.fontText, fontSize: 11, color: TOKENS.inkMuted }}>
          no image
        </div>
      )}
      {hovered && canLocate && (
        <HighlightLocatorTooltip
          anchorRect={anchorRect}
          bit={bit}
          color={color}
          moleculeSmiles={sourceSmiles}
          subInfo={subInfo}
          highlightDirection={highlightDirection}
          tooltipBorder={tooltipBorder}
        />
      )}
    </div>
  );
};

const InlineComparison = ({ smilesPair }) => {
  const [smiles1, smiles2] = smilesPair ?? [];
  const { data, isLoading, isError } = useQuery({
    queryKey: ['chat-inline-comparison', smiles1, smiles2],
    queryFn: () => comparePredictions(smiles1, smiles2),
    enabled: !!smiles1 && !!smiles2,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (!smiles1 || !smiles2 || isError) return null;
  if (isLoading) {
    return (
      <div style={{
        marginBottom: 12,
        padding: 12,
        borderRadius: 14,
        background: 'rgba(255,255,255,0.58)',
        boxShadow: '0 1px 0 rgba(255,255,255,0.78) inset, 0 0 0 1px rgba(15,18,28,0.06)',
        fontFamily: TOKENS.fontText,
        fontSize: 12.5,
        color: TOKENS.inkMuted,
        whiteSpace: 'normal',
      }}>
        Building comparison card...
      </div>
    );
  }
  if (!data?.mol1 || !data?.mol2) return null;

  const p1 = Number(data.mol1.probability_active ?? 0);
  const p2 = Number(data.mol2.probability_active ?? 0);
  const delta = Number(data.delta_probability ?? (p2 - p1));
  const winner = p1 >= p2 ? 'mol1' : 'mol2';
  const topBits = (data.top_differentiating_bits ?? []).slice(0, 3);
  const maxAbs = topBits.reduce((acc, bit) => Math.max(acc, Math.abs(Number(bit.shap_diff ?? 0))), 0);

  return (
    <div style={{
      marginBottom: 14,
      padding: 14,
      borderRadius: 16,
      background: 'rgba(255,255,255,0.74)',
      boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.07)',
      whiteSpace: 'normal',
    }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 130px 1fr', gap: 12, alignItems: 'stretch' }}>
        <CompareMoleculePanel label="Molecule 1" result={data.mol1} winner={winner === 'mol1'} />
        <div style={{
          display: 'grid',
          placeItems: 'center',
          alignContent: 'center',
          gap: 10,
          padding: '10px 8px',
          borderRadius: 14,
          background: 'rgba(15,18,28,0.04)',
          boxShadow: '0 0 0 1px rgba(15,18,28,0.05)',
        }}>
          <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: TOKENS.inkMuted }}>
            Delta P(active)
          </div>
          <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 24, fontWeight: 800, color: delta >= 0 ? 'oklch(60% 0.13 155)' : 'oklch(58% 0.16 28)', letterSpacing: 0 }}>
            {formatSigned(delta)}
          </div>
          <div style={{ width: '100%', height: 10, borderRadius: 999, background: 'rgba(15,18,28,0.08)', position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: 'rgba(15,18,28,0.28)' }} />
            <div style={{
              position: 'absolute',
              top: 2,
              bottom: 2,
              left: delta >= 0 ? '50%' : `${50 - Math.min(50, Math.abs(delta) * 50)}%`,
              width: `${Math.max(6, Math.min(50, Math.abs(delta) * 50))}%`,
              borderRadius: 999,
              background: delta >= 0 ? 'oklch(60% 0.13 155)' : 'oklch(58% 0.16 28)',
            }} />
          </div>
          <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.inkMuted, textAlign: 'center' }}>
            mol2 - mol1<br />Tanimoto {formatProb(Number(data.tanimoto))}
          </div>
        </div>
        <CompareMoleculePanel label="Molecule 2" result={data.mol2} winner={winner === 'mol2'} />
      </div>

      {topBits.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 800, color: TOKENS.inkSoft, marginBottom: 2 }}>
            Top differentiating SHAP bits
          </div>
          {topBits.map(bit => (
            <ComparisonBitRow
              key={bit.bit}
              bit={bit}
              maxAbs={maxAbs}
              mol1Smiles={data.mol1.canonical_smiles}
              mol2Smiles={data.mol2.canonical_smiles}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const BitDatabaseCard = ({ intent }) => {
  const modeOrBit = intent?.mode && intent.mode !== 'active-on-most-ambiguous' ? intent.mode : intent?.bitIndex;
  const { data, isLoading, isError } = useQuery({
    queryKey: ['chat-bit-database', intent?.mode ?? 'bit', modeOrBit ?? null, intent?.smiles ?? null],
    queryFn: () => intent?.mode === 'active-on-most-ambiguous'
      ? getActiveOnMostAmbiguousBit(intent.smiles)
      : getBitDatabaseInfo(modeOrBit),
    enabled: intent?.mode === 'active-on-most-ambiguous'
      ? !!intent?.smiles
      : modeOrBit !== undefined && modeOrBit !== null,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (!intent || isError) return null;
  if (isLoading) {
    return (
      <div style={{
        marginBottom: 12,
        padding: 12,
        borderRadius: 14,
        background: 'rgba(255,255,255,0.58)',
        boxShadow: '0 1px 0 rgba(255,255,255,0.78) inset, 0 0 0 1px rgba(15,18,28,0.06)',
        fontFamily: TOKENS.fontText,
        fontSize: 12.5,
        color: TOKENS.inkMuted,
        whiteSpace: 'normal',
      }}>
        Building bit-collision card...
      </div>
    );
  }
  if (!data) return null;

  const confidence = data.collision_confidence ?? {};
  const evidence = data.evidence_confidence ?? {};
  const confidenceColor = confidence.level === 'low'
    ? 'oklch(58% 0.16 28)'
    : confidence.level === 'moderate'
      ? 'oklch(63% 0.14 72)'
      : 'oklch(60% 0.13 155)';
  const evidenceColor = evidence.level === 'sufficient'
    ? 'oklch(60% 0.13 155)'
    : evidence.level === 'limited'
      ? 'oklch(63% 0.14 72)'
      : 'oklch(58% 0.16 28)';
  const isCollision = Number(data.n_unique_substructures) > 1;

  return (
    <div style={{
      marginBottom: 14,
      padding: 14,
      borderRadius: 16,
      background: 'rgba(255,255,255,0.74)',
      boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.07)',
      whiteSpace: 'normal',
    }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 210px', gap: 16, alignItems: 'start' }}>
        <div>
          <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: TOKENS.inkMuted }}>
            Training-set bit database
          </div>
          <div style={{ marginTop: 4, fontFamily: TOKENS.fontDisplay, fontSize: 25, fontWeight: 800, color: TOKENS.ink, letterSpacing: 0 }}>
            {data.bit}
          </div>
          <div style={{ marginTop: 8, fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkSoft, lineHeight: 1.45 }}>
            {isCollision
              ? 'Bit collision is present: multiple distinct training-set atom environments hash to this same folded ECFP bit.'
              : 'No bit collision was observed for this bit in the loaded training set.'}
            {' '}This becomes difficult to interpret when no substructure dominates the activations.
            {data.molecule_context && (
              <>
                {' '}For the queried molecule this bit is ON; the grid below shows the training-set collision profile.
              </>
            )}
          </div>
        </div>
        <div style={{ display: 'grid', gap: 7 }}>
          {[
            ['activations', data.total_activations],
            ['active ratio', `${(Number(data.active_ratio) * 100).toFixed(1)}%`],
            ['unique substructures', data.n_unique_substructures],
            ['dominance', `${Number(data.dominance).toFixed(1)}%`],
          ].map(([label, value]) => (
            <div key={label} style={{ display: 'flex', justifyContent: 'space-between', gap: 10, fontFamily: TOKENS.fontText, fontSize: 12, color: TOKENS.inkSoft }}>
              <span style={{ color: TOKENS.inkMuted }}>{label}</span>
              <span style={{ fontWeight: 800, color: TOKENS.ink }}>{value}</span>
            </div>
          ))}
          <div style={{
            marginTop: 4,
            padding: '7px 9px',
            borderRadius: 10,
            background: 'rgba(15,18,28,0.05)',
            color: confidenceColor,
            fontFamily: TOKENS.fontText,
            fontSize: 11.5,
            fontWeight: 800,
            lineHeight: 1.35,
          }}>
            {confidence.label}
          </div>
          {evidence.label && (
            <div style={{
              padding: '7px 9px',
              borderRadius: 10,
              background: 'rgba(15,18,28,0.05)',
              color: evidenceColor,
              fontFamily: TOKENS.fontText,
              fontSize: 11.5,
              fontWeight: 800,
              lineHeight: 1.35,
            }}>
              {evidence.label}
            </div>
          )}
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 800, color: TOKENS.inkSoft, marginBottom: 8 }}>
          Mapped substructures contributing to this folded bit
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(146px, 1fr))',
          gap: 9,
        }}>
          {(data.substructures ?? []).map((sub, index) => (
            <div key={`${sub.smiles}-${index}`} style={{
              display: 'grid',
              gridTemplateRows: '78px auto auto',
              gap: 7,
              padding: 8,
              borderRadius: 12,
              background: sub.smiles === data.dominant_substructure ? 'rgba(9,128,72,0.08)' : 'rgba(255,255,255,0.62)',
              boxShadow: sub.smiles === data.dominant_substructure
                ? '0 0 0 1px oklch(60% 0.13 155 / 0.25)'
                : '0 0 0 1px rgba(15,18,28,0.05)',
              minWidth: 0,
            }}>
              <div style={{
                position: 'relative',
                borderRadius: 9,
                background: '#fff',
                boxShadow: '0 0 0 1px rgba(15,18,28,0.05)',
                overflow: 'hidden',
                display: 'grid',
                placeItems: 'center',
              }}>
                <img
                  src={moleculeImageUrl(sub.smiles, 160, 110)}
                  alt={sub.smiles}
                  loading="lazy"
                  decoding="async"
                  onError={event => { event.currentTarget.style.visibility = 'hidden'; }}
                  style={{ width: '100%', height: 76, objectFit: 'contain' }}
                />
                {sub.smiles === data.dominant_substructure && (
                  <div style={{
                    position: 'absolute',
                    top: 6,
                    left: 6,
                    padding: '2px 6px',
                    borderRadius: 999,
                    background: 'rgba(9,128,72,0.10)',
                    color: 'oklch(60% 0.13 155)',
                    fontFamily: TOKENS.fontText,
                    fontSize: 10,
                    fontWeight: 900,
                  }}>
                    dominant
                  </div>
                )}
              </div>
              <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 800, color: TOKENS.ink, overflowWrap: 'anywhere', lineHeight: 1.25 }}>
                {sub.smiles}
              </div>
              <div style={{
                justifySelf: 'start',
                padding: '3px 7px',
                borderRadius: 999,
                background: 'rgba(15,18,28,0.05)',
                fontFamily: TOKENS.fontText,
                fontSize: 11,
                fontWeight: 800,
                color: TOKENS.inkMuted,
              }}>
                {sub.count} hits · {Number(sub.percentage).toFixed(1)}%
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const ChartShell = ({ title, subtitle, children }) => (
  <div style={{
    marginBottom: 14,
    padding: 14,
    borderRadius: 16,
    background: 'rgba(255,255,255,0.74)',
    boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px rgba(15,18,28,0.07)',
    whiteSpace: 'normal',
  }}>
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 800, letterSpacing: '0.08em', textTransform: 'uppercase', color: TOKENS.inkMuted }}>
        {title}
      </div>
      {subtitle && (
        <div style={{ marginTop: 3, fontFamily: TOKENS.fontText, fontSize: 12.5, color: TOKENS.inkSoft }}>
          {subtitle}
        </div>
      )}
    </div>
    {children}
  </div>
);

const LoadingVisualCard = () => (
  <div style={{
    marginBottom: 12,
    padding: 12,
    borderRadius: 14,
    background: 'rgba(255,255,255,0.58)',
    boxShadow: '0 1px 0 rgba(255,255,255,0.78) inset, 0 0 0 1px rgba(15,18,28,0.06)',
    fontFamily: TOKENS.fontText,
    fontSize: 12.5,
    color: TOKENS.inkMuted,
    whiteSpace: 'normal',
  }}>
    Building visual summary...
  </div>
);

const HorizontalBars = ({ rows }) => {
  const max = Math.max(1, ...rows.map(row => Number(row.value) || 0));
  return (
    <div style={{ display: 'grid', gap: 9 }}>
      {rows.map(row => (
        <div key={row.label} style={{ display: 'grid', gridTemplateColumns: '112px minmax(0, 1fr) 72px', gap: 10, alignItems: 'center' }}>
          <div style={{ fontFamily: TOKENS.fontText, fontSize: 12, fontWeight: 800, color: TOKENS.inkSoft }}>{row.label}</div>
          <div style={{ height: 14, borderRadius: 999, background: 'rgba(15,18,28,0.07)', overflow: 'hidden' }}>
            <div style={{
              width: `${Math.max(2, Math.min(100, (Number(row.value) / max) * 100))}%`,
              height: '100%',
              borderRadius: 999,
              background: row.color ?? 'oklch(60% 0.13 155)',
            }} />
          </div>
          <div style={{ textAlign: 'right', fontFamily: TOKENS.fontDisplay, fontSize: 17, fontWeight: 800, color: TOKENS.ink, letterSpacing: 0 }}>
            {row.value}
          </div>
        </div>
      ))}
    </div>
  );
};

const MetricBars = ({ rows }) => (
  <div style={{ display: 'grid', gridTemplateColumns: `repeat(${rows.length}, minmax(0, 1fr))`, gap: 10 }}>
    {rows.map(row => {
      const value = Number(row.value ?? 0);
      return (
        <div key={row.label} style={{
          padding: 10,
          borderRadius: 13,
          background: 'rgba(255,255,255,0.65)',
          boxShadow: '0 0 0 1px rgba(15,18,28,0.05)',
        }}>
          <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 800, color: TOKENS.inkMuted }}>{row.label}</div>
          <div style={{ marginTop: 4, fontFamily: TOKENS.fontDisplay, fontSize: 24, fontWeight: 800, color: row.color, letterSpacing: 0 }}>
            {Number.isFinite(value) ? value.toFixed(3) : 'n/a'}
          </div>
          <div style={{ marginTop: 8, height: 10, borderRadius: 999, background: 'rgba(15,18,28,0.08)', overflow: 'hidden' }}>
            <div style={{ width: `${Math.max(1, Math.min(100, value * 100))}%`, height: '100%', borderRadius: 999, background: row.color }} />
          </div>
        </div>
      );
    })}
  </div>
);

const Donut = ({ active, inactive }) => {
  const total = Math.max(1, Number(active) + Number(inactive));
  const activePct = Number(active) / total;
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '116px minmax(0, 1fr)', gap: 16, alignItems: 'center' }}>
      <svg width="116" height="116" viewBox="0 0 116 116" aria-label="Class balance donut">
        <circle cx="58" cy="58" r={radius} fill="none" stroke="rgba(15,18,28,0.10)" strokeWidth="16" />
        <circle
          cx="58"
          cy="58"
          r={radius}
          fill="none"
          stroke="oklch(60% 0.13 155)"
          strokeWidth="16"
          strokeDasharray={`${activePct * circumference} ${circumference}`}
          strokeLinecap="round"
          transform="rotate(-90 58 58)"
        />
        <text x="58" y="54" textAnchor="middle" style={{ fontFamily: TOKENS.fontDisplay, fontSize: 18, fontWeight: 800, fill: TOKENS.ink }}>
          {(activePct * 100).toFixed(1)}%
        </text>
        <text x="58" y="72" textAnchor="middle" style={{ fontFamily: TOKENS.fontText, fontSize: 10, fontWeight: 800, fill: TOKENS.inkMuted }}>
          Active
        </text>
      </svg>
      <HorizontalBars rows={[
        { label: 'Active', value: active, color: 'oklch(60% 0.13 155)' },
        { label: 'Inactive', value: inactive, color: 'oklch(58% 0.16 28)' },
      ]} />
    </div>
  );
};

const ConfusionHeatmap = ({ matrix }) => {
  if (!matrix) return null;
  const values = [matrix?.[0]?.[0], matrix?.[0]?.[1], matrix?.[1]?.[0], matrix?.[1]?.[1]].map(value => Number(value) || 0);
  const max = Math.max(1, ...values);
  const cells = [
    { label: 'True inactive', sub: 'TN', value: values[0], good: true },
    { label: 'False active', sub: 'FP', value: values[1], good: false },
    { label: 'False inactive', sub: 'FN', value: values[2], good: false },
    { label: 'True active', sub: 'TP', value: values[3], good: true },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 9 }}>
      {cells.map(cell => {
        const alpha = 0.08 + 0.34 * (cell.value / max);
        const bg = cell.good ? `rgba(9,128,72,${alpha})` : `rgba(190,42,28,${alpha})`;
        return (
          <div key={cell.sub} style={{
            minHeight: 82,
            padding: 11,
            borderRadius: 12,
            background: bg,
            boxShadow: '0 0 0 1px rgba(15,18,28,0.06)',
            display: 'grid',
            alignContent: 'space-between',
          }}>
            <div style={{ fontFamily: TOKENS.fontText, fontSize: 11.5, fontWeight: 800, color: TOKENS.inkMuted }}>{cell.sub} · {cell.label}</div>
            <div style={{ fontFamily: TOKENS.fontDisplay, fontSize: 27, fontWeight: 800, color: TOKENS.ink, letterSpacing: 0 }}>{cell.value}</div>
          </div>
        );
      })}
    </div>
  );
};

const ChatDataVisual = ({ intent }) => {
  const needsStatus = intent?.type === 'dataset-sizes';
  const needsEvaluation = ['class-balance', 'metric-bars', 'confusion-matrix'].includes(intent?.type);
  const statusQ = useQuery({ queryKey: ['chat-visual-status'], queryFn: getModelStatus, enabled: needsStatus, retry: false, staleTime: 60 * 1000 });
  const evalQ = useQuery({ queryKey: ['chat-visual-evaluation'], queryFn: getEvaluation, enabled: needsEvaluation, retry: false, staleTime: 60 * 1000 });

  if (!intent) return null;
  if ((needsStatus && statusQ.isLoading) || (needsEvaluation && evalQ.isLoading)) return <LoadingVisualCard />;
  if ((needsStatus && statusQ.isError) || (needsEvaluation && evalQ.isError)) return null;

  if (intent.type === 'dataset-sizes') {
    const status = statusQ.data;
    return (
      <ChartShell title="Dataset size" subtitle="Loaded molecules by split">
        <HorizontalBars rows={[
          { label: 'Training', value: status?.n_molecules ?? 0, color: 'oklch(60% 0.13 155)' },
          { label: 'Test', value: status?.n_test ?? 0, color: 'oklch(63% 0.14 72)' },
        ]} />
      </ChartShell>
    );
  }

  if (intent.type === 'class-balance') {
    const data = evalQ.data;
    const isTest = intent.split === 'test';
    const active = isTest ? data?.test_n_active : data?.n_active;
    const inactive = isTest ? data?.test_n_inactive : data?.n_inactive;
    if (active == null || inactive == null) return null;
    return (
      <ChartShell title={`${isTest ? 'Test' : 'Training'} class balance`} subtitle="Active vs Inactive molecules">
        <Donut active={active} inactive={inactive} />
      </ChartShell>
    );
  }

  if (intent.type === 'metric-bars') {
    const data = evalQ.data;
    const rows = [
      { label: 'Test ROC-AUC', value: data?.test_roc_auc ?? data?.roc_auc, color: 'oklch(60% 0.13 155)' },
      { label: 'Test PR-AUC', value: data?.test_pr_auc ?? data?.pr_auc, color: 'oklch(63% 0.14 72)' },
    ];
    return (
      <ChartShell title="Model performance" subtitle="Higher values indicate better ranking performance">
        <MetricBars rows={rows} />
      </ChartShell>
    );
  }

  if (intent.type === 'confusion-matrix') {
    const data = evalQ.data;
    const matrix = data?.test_confusion_matrix ?? data?.confusion_matrix;
    return (
      <ChartShell title="Confusion matrix" subtitle="Default threshold: P(active) = 0.5">
        <ConfusionHeatmap matrix={matrix} />
      </ChartShell>
    );
  }

  return null;
};

function extractMoleculePatterns(text) {
  const found = [];
  const seen = new Set();
  for (const match of text.matchAll(MOLECULE_TOKEN_RE)) {
    const raw = (match[1] ?? match[0] ?? '').trim().replace(/[.,;:)]+$/g, '');
    if (raw.length < MOLECULE_MIN_CHARS) continue;
    if (!/[A-Za-z\[\]#=()]/.test(raw)) continue;
    if (!/[cnospBCNOFPSI\[\]#=()]/.test(raw)) continue;
    if (/^(active|inactive|smiles|smart|smarts|model|dataset|prediction|probability)$/i.test(raw)) continue;
    if (seen.has(raw)) continue;
    seen.add(raw);
    found.push(raw);
    if (found.length >= 4) break;
  }
  return found;
}

const MoleculePreviewStrip = ({ content }) => {
  const patterns = extractMoleculePatterns(content);
  if (!patterns.length) return null;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${Math.min(patterns.length, 2)}, minmax(0, 1fr))`, gap: 10, marginTop: 12 }}>
      {patterns.map(pattern => (
        <div key={pattern} style={{
          padding: 9,
          borderRadius: 12,
          background: 'rgba(255,255,255,0.72)',
          boxShadow: '0 1px 0 rgba(255,255,255,0.8) inset, 0 0 0 1px rgba(15,18,28,0.06)',
        }}>
          <img
            src={moleculeImageUrl(pattern, 220, 130)}
            alt={pattern}
            loading="lazy"
            decoding="async"
            onError={event => { event.currentTarget.parentElement.style.display = 'none'; }}
            style={{ width: '100%', height: 104, objectFit: 'contain', display: 'block', background: '#fff', borderRadius: 9 }}
          />
          <div style={{ marginTop: 7, fontFamily: TOKENS.fontMono, fontSize: 10.5, color: TOKENS.inkMuted, overflowWrap: 'anywhere' }}>{pattern}</div>
        </div>
      ))}
    </div>
  );
};

/* ---------- The page ---------- */
const ChatPage = () => {
  const modelLoaded = useAppStore(s => s.modelLoaded);
  const [initialChatState] = useState(loadChatState);
  const [messages, setMessages] = useState(initialChatState.messages ?? []);
  const [input, setInput] = useState('');
  const [recentChats, setRecentChats] = useState(initialChatState.recentChats ?? []);
  const [currentChatId, setCurrentChatId] = useState(initialChatState.currentChatId ?? null);
  const [selectedChatIds, setSelectedChatIds] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (!currentChatId) return;
    setRecentChats(current => current.map(chat => (
      chat.id === currentChatId ? { ...chat, messages } : chat
    )));
  }, [currentChatId, messages]);

  useEffect(() => {
    saveChatState({ recentChats, currentChatId, messages });
  }, [recentChats, currentChatId, messages]);

  async function send(value = input) {
    const text = value.trim();
    if (!text || streaming) return;
    const smilesPair = extractQuerySmilesPair(text);
    const querySmiles = smilesPair ? null : extractQuerySmiles(text);
    const bitDbIntent = smilesPair ? null : extractBitDatabaseIntent(text, querySmiles);
    const predictionIntent = smilesPair || bitDbIntent ? null : extractMoleculePredictionIntent(text);
    const chartIntent = smilesPair || bitDbIntent || predictionIntent ? null : extractChartIntent(text);
    const smiles = smilesPair || bitDbIntent ? null : querySmiles;
    const smilesContext = smiles ?? bitDbIntent?.smiles ?? undefined;
    setInput('');
    const makeId = () => (crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random()));
    let chatId = currentChatId;
    if (!chatId) {
      chatId = makeId();
      setCurrentChatId(chatId);
      setRecentChats(current => [
        { id: chatId, title: text.length > 34 ? `${text.slice(0, 34)}...` : text, messages: [] },
        ...current,
      ]);
    }
    setMessages(current => [
      ...current,
      { id: makeId(), role: 'user', content: text },
      {
        id: makeId(),
        role: 'assistant',
        content: '',
        predictSmiles: smiles,
        predictionIntent,
        compareSmiles: smilesPair,
        bitDbIntent,
        chartIntent,
      },
    ]);
    setStreaming(true);

    try {
      let gotChunk = false;
      for await (const chunk of streamChat(text, true, smilesContext)) {
        gotChunk = true;
        setMessages(current => {
          const copy = [...current];
          const last = copy[copy.length - 1];
          copy[copy.length - 1] = { ...last, content: last.content + chunk };
          return copy;
        });
      }
      if (!gotChunk) {
        const data = await chatSimple(text, true, smilesContext);
        setMessages(current => {
          const copy = [...current];
          copy[copy.length - 1] = { ...copy[copy.length - 1], content: data.response };
          return copy;
        });
      }
    } catch (error) {
      setMessages(current => {
        const copy = [...current];
        copy[copy.length - 1] = { ...copy[copy.length - 1], content: `Chat unavailable: ${error.message ?? String(error)}` };
        return copy;
      });
    } finally {
      setStreaming(false);
    }
  }

  const prompt = value => {
    setInput(value);
    send(value);
  };
  const newChat = () => {
    setMessages([]);
    setInput('');
    setCurrentChatId(null);
  };
  const selectRecent = id => {
    const chat = recentChats.find(item => item.id === id);
    if (!chat) return;
    setCurrentChatId(chat.id);
    setMessages(chat.messages ?? []);
  };
  const toggleRecentSelection = id => {
    setSelectedChatIds(current => (
      current.includes(id) ? current.filter(item => item !== id) : [...current, id]
    ));
  };
  const clearSelectedChats = () => {
    if (!selectedChatIds.length) return;
    const selected = new Set(selectedChatIds);
    setRecentChats(current => current.filter(chat => !selected.has(chat.id)));
    setSelectedChatIds([]);
    if (currentChatId && selected.has(currentChatId)) {
      setCurrentChatId(null);
      setMessages([]);
      setInput('');
    }
  };
  const clearAllChats = () => {
    if (!recentChats.length) return;
    setRecentChats([]);
    setSelectedChatIds([]);
    setCurrentChatId(null);
    setMessages([]);
    setInput('');
  };

  return (
  <div style={{ width: 1440, height: 1024, position: 'relative', fontFamily: TOKENS.fontText, color: TOKENS.ink }}>
    <MeshBackground>
      <div style={{ display: 'flex', height: '100%' }}>
        <ChatSidebar
          recents={recentChats}
          selectedIds={selectedChatIds}
          currentChatId={currentChatId}
          onSelectRecent={selectRecent}
          onToggleRecent={toggleRecentSelection}
          onClearSelected={clearSelectedChats}
          onClearAll={clearAllChats}
        />

        <div data-glass-main="chat" style={{ flex: 1, height: '100%', overflow: 'hidden', padding: '8px 20px 20px 4px', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          {/* Top bar */}
          <Glass tone="A" radius={20} padding={0} style={{ marginBottom: 22 }}>
            <ChatTopBar/>
          </Glass>

          {/* Page header */}
          <div style={{ padding: '4px 6px 18px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 24 }}>
              <div>
                <Label style={{ marginBottom: 12, color: TOKENS.accent }}>WORKSPACE - CHAT</Label>
                <h1 style={{ margin: 0, fontFamily: TOKENS.fontDisplay, fontSize: 56, fontWeight: 700, letterSpacing: '-0.035em', lineHeight: 1, color: TOKENS.ink }}>
                  Chat
                </h1>
                <div style={{ marginTop: 14, fontFamily: TOKENS.fontText, fontSize: 15, color: TOKENS.inkMuted, maxWidth: 620, lineHeight: 1.5 }}>
                  Ask questions about molecules, predictions, and model explanations.
                </div>
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <ButtonGhost icon="layers" onClick={selectedChatIds.length ? clearSelectedChats : clearAllChats} disabled={!recentChats.length}>
                  {selectedChatIds.length ? 'Delete selected' : 'Clear history'}
                </ButtonGhost>
                <ButtonGhost icon="plus" onClick={newChat}>New chat</ButtonGhost>
              </div>
            </div>
          </div>

          {/* Conversation area (empty state) */}
          <div style={{
            flex: 1, minHeight: 0,
            display: 'flex', flexDirection: 'column', alignItems: messages.length ? 'stretch' : 'center', justifyContent: messages.length ? 'flex-start' : 'center',
            gap: 28,
            padding: '20px 60px',
            overflowY: 'auto',
          }} data-chat-scroll>
            {messages.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 900, width: '100%', margin: '0 auto' }}>
                {messages.map((message, index) => {
                  const visualPair = message.role === 'assistant' ? message.compareSmiles : null;
                  const visualBitDb = message.role === 'assistant' ? message.bitDbIntent : null;
                  const visualChart = message.role === 'assistant' ? message.chartIntent : null;
                  const visualSmiles = message.role === 'assistant'
                    ? (visualPair || visualBitDb || visualChart ? null : (message.predictSmiles ?? extractCanonicalSmiles(message.content)))
                    : null;
                  return (
                    <div key={message.id} style={{ display: 'flex', justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start' }}>
                      <div style={{
                        maxWidth: visualPair ? 920 : (visualBitDb ? 860 : (visualChart ? 760 : (visualSmiles ? 780 : 680))),
                        padding: '14px 16px',
                        borderRadius: message.role === 'user' ? '18px 18px 6px 18px' : '18px 18px 18px 6px',
                        background: message.role === 'user'
                          ? 'linear-gradient(180deg, oklch(70% 0.13 155), oklch(58% 0.13 155))'
                          : 'rgba(255,255,255,0.62)',
                        color: message.role === 'user' ? '#fff' : TOKENS.ink,
                        boxShadow: message.role === 'user'
                          ? '0 1px 0 rgba(255,255,255,0.35) inset, 0 0 0 1px oklch(48% 0.13 155 / 0.5), 0 8px 18px -8px oklch(50% 0.13 155 / 0.45)'
                          : TOKENS.shadowCard,
                        backdropFilter: 'blur(30px) saturate(160%)',
                        WebkitBackdropFilter: 'blur(30px) saturate(160%)',
                        fontFamily: TOKENS.fontText,
                        fontSize: 14.5,
                        lineHeight: 1.55,
                        whiteSpace: 'pre-wrap',
                      }}>
                        {visualPair && <InlineComparison smilesPair={visualPair} />}
                        {visualBitDb && <BitDatabaseCard intent={visualBitDb} />}
                        {visualChart && <ChatDataVisual intent={visualChart} />}
                        {visualSmiles && <InlinePrediction smiles={visualSmiles} intent={message.predictionIntent} />}
                        {message.content}
                        {message.role === 'assistant' && message.content && !visualSmiles && !visualPair && !visualBitDb && !visualChart && (
                          <MoleculePreviewStrip content={message.content}/>
                        )}
                        {streaming && index === messages.length - 1 && message.role === 'assistant' && (
                          <span style={{ display: 'inline-block', width: 6, height: 16, marginLeft: 4, borderRadius: 3, background: TOKENS.accent, verticalAlign: 'text-bottom' }} />
                        )}
                      </div>
                    </div>
                  );
                })}
                <div ref={bottomRef} />
              </div>
            ) : (
              <>
            {/* Hero glyph */}
            <div style={{ position: 'relative', display: 'grid', placeItems: 'center' }}>
              <div style={{
                position: 'absolute', inset: -42,
                background: 'radial-gradient(closest-side, oklch(80% 0.13 90 / 0.35), transparent 70%)',
                pointerEvents: 'none',
              }}/>
              <div style={{
                width: 78, height: 78, borderRadius: 22,
                background: 'linear-gradient(180deg, oklch(94% 0.12 90 / 0.85), oklch(86% 0.13 70 / 0.75))',
                display: 'grid', placeItems: 'center',
                color: 'oklch(45% 0.15 65)',
                boxShadow: '0 1px 0 rgba(255,255,255,0.9) inset, 0 0 0 1px oklch(70% 0.13 85 / 0.4), 0 16px 40px -12px oklch(60% 0.15 75 / 0.35)',
              }}>
                <Icon name="sparkle" size={36}/>
              </div>
            </div>

            <div style={{ textAlign: 'center', maxWidth: 540 }}>
              <h2 style={{
                margin: 0,
                fontFamily: TOKENS.fontDisplay, fontSize: 36, fontWeight: 700,
                letterSpacing: '-0.025em', color: TOKENS.ink,
              }}>Ask me anything</h2>
              <div style={{
                marginTop: 10,
                fontFamily: TOKENS.fontText, fontSize: 15, color: TOKENS.inkMuted, lineHeight: 1.55,
              }}>
                Molecules, bioactivity, SHAP values, model explanations - the assistant has the dataset and model loaded.
              </div>
            </div>

            {/* Suggestion cards */}
            <div style={{ display: 'flex', gap: 14, width: '100%', maxWidth: 940 }}>
              <SuggestionCard
                icon="db" title="Summarize dataset"
                sub="Class balance, descriptor distributions, top scaffolds."
                prompt='"Give me a one-page summary of the training set."'
                onClick={() => prompt('Give me a one-page summary of the training set.')}
              />
              <SuggestionCard
                icon="flask" title="Explain prediction"
                sub="Walk through the activity probability for a given SMILES."
                prompt='predict "O=C(Nc1ccccc1)c1ccnccc1"'
                onClick={() => prompt('predict "O=C(Nc1ccccc1)c1ccnccc1"')}
              />
              <SuggestionCard
                icon="chart" title="Read SHAP values"
                sub="Which substructures pushed the score up or down?"
                prompt='"Top 3 positive SHAP features for compound #214."'
                onClick={() => prompt('Top 3 positive SHAP features for compound #214.')}
              />
            </div>

            {/* Example chips */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
              <ExampleChip onClick={() => prompt('What does AD = 0.15 mean?')}>What does AD = 0.15 mean?</ExampleChip>
              <ExampleChip onClick={() => prompt('Compare iters 3 and 5')}>Compare iters 3 and 5</ExampleChip>
              <ExampleChip onClick={() => prompt('List Lipinski-violating candidates')}>List Lipinski-violating candidates</ExampleChip>
            </div>
              </>
            )}
          </div>

          {/* Composer */}
          <Glass tone="A" radius={22} padding={10} style={{
            display: 'flex', alignItems: 'center', gap: 10,
            flex: '0 0 auto',
          }}>
            {/* Context chip cluster */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '5px 9px 5px 7px',
                background: 'oklch(66% 0.115 155 / 0.14)',
                borderRadius: 8,
                fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.accentInk, fontWeight: 600,
              }}>
                <Icon name="db" size={12}/>
                Dataset
              </div>
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '5px 9px 5px 7px',
                background: 'oklch(66% 0.115 155 / 0.14)',
                borderRadius: 8,
                fontFamily: TOKENS.fontText, fontSize: 11.5, color: TOKENS.accentInk, fontWeight: 600,
              }}>
                <Icon name="cpu" size={12}/>
                Model
              </div>
            </div>

            {/* Input */}
            <textarea
              value={input}
              onChange={event => setInput(event.target.value)}
              onKeyDown={event => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  send();
                }
              }}
              rows={1}
              placeholder="Ask something about the dataset or the model..."
              style={{
                flex: 1,
                height: 48,
                resize: 'none',
                padding: '0 14px',
                border: 'none',
                outline: 'none',
                background: 'transparent',
                fontFamily: TOKENS.fontText, fontSize: 14.5, color: TOKENS.ink, letterSpacing: '-0.005em',
                lineHeight: '48px',
              }}
            />
            <div style={{
              flex: 1,
              height: 48,
              display: 'none', alignItems: 'center',
              padding: '0 14px',
              fontFamily: TOKENS.fontText, fontSize: 14.5, color: TOKENS.inkFaint, letterSpacing: '-0.005em',
            }}>
              Ask something about the dataset or the model...
            </div>

            {/* Send */}
            <button type="button" onClick={() => send()} disabled={!input.trim() || streaming} style={{
              appearance: 'none', border: 'none', cursor: !input.trim() || streaming ? 'not-allowed' : 'pointer',
              width: 48, height: 48, borderRadius: 14,
              background: `linear-gradient(180deg, oklch(70% 0.13 155), oklch(58% 0.13 155))`,
              color: '#fff',
              display: 'grid', placeItems: 'center',
              boxShadow: '0 1px 0 rgba(255,255,255,0.35) inset, 0 0 0 1px oklch(48% 0.13 155 / 0.5), 0 6px 14px -4px oklch(50% 0.13 155 / 0.45)',
              opacity: !input.trim() || streaming ? 0.55 : 1,
            }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m4 12 16-8-6 18-2-8-8-2Z"/>
              </svg>
            </button>
          </Glass>

        </div>
      </div>
    </MeshBackground>
  </div>
  );
};

export default ChatPage;




