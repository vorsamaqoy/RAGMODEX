import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { streamChat, chatSimple, predict, moleculeImageUrl } from '../lib/api'
import { useAppStore } from '../store'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { ProbBar } from '../components/ui/ProbBar'
import { Send, Bot, User, Sparkles, FlaskConical, BarChart3, Database, ArrowDown, ArrowUp } from 'lucide-react'
import { cn } from '../lib/cn'

// ── types ─────────────────────────────────────────────────────────────────────

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  predictSmiles?: string
}

// ── SMILES extraction ─────────────────────────────────────────────────────────

function extractSmiles(text: string): string | null {
  const t = text.trim()
  const m0 = t.match(/\bfor\s+molecule\s+["']?([A-Za-z0-9@+\-\[\]\\/#%().=]{4,})["']?\s*[,.;:]/i)
  if (m0) return m0[1]
  const mSmiles = t.match(/\bSMILES\s*[:=]\s*["']?([A-Za-z0-9@+\-\[\]\\/#%().=]{4,})["']?/i)
  if (mSmiles) return mSmiles[1]
  const m1 = t.match(/^(?:predict|analyze|interpret)\s+["']([^"']{5,})["']/i)
  if (m1) return m1[1]
  const m2 = t.match(/^(?:predict|analyze|interpret)\s+([A-Za-z][A-Za-z0-9@+\-\[\]\\/#%().=]{4,})/i)
  if (m2) return m2[1]
  const m3 = t.match(/["']([A-Za-z][A-Za-z0-9@+\-\[\]\\/#%().=*]{4,})["']/)
  if (m3) return m3[1]
  return null
}

// ── InlinePrediction ──────────────────────────────────────────────────────────

function activityTone(value: number) {
  if (value >= 0.7) return { label: 'High active probability', color: 'oklch(66% 0.115 155)', bg: 'rgb(0 215 34 / 0.10)' }
  if (value >= 0.4) return { label: 'Borderline activity', color: 'oklch(78% 0.14 70)', bg: 'rgb(255 174 19 / 0.13)' }
  return { label: 'Low active probability', color: 'oklch(70% 0.16 25)', bg: 'rgb(239 68 68 / 0.10)' }
}

function ShapBitRow({ bit, maxAbs }: { bit: NonNullable<Awaited<ReturnType<typeof predict>>>['top_bits'][number], maxAbs: number }) {
  const shap = bit.shap_value
  const positive = shap >= 0
  const width = Math.max(6, Math.min(50, (Math.abs(shap) / Math.max(maxAbs, 0.000001)) * 50))
  const sub = bit.molecule_substructures?.[0]?.smiles
    ?? bit.training_info?.dominant_substructure
    ?? 'No mapped substructure'
  const confidence = bit.training_info
    ? bit.training_info.n_unique_substructures <= 1
      ? 'clear'
      : bit.training_info.dominance > 80
        ? 'dominant'
        : 'mixed'
    : 'no training context'

  return (
    <div className="rounded-md border border-border-subtle bg-white/45 p-3 shadow-[0_1px_0_rgb(255_255_255_/_0.6)_inset]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="t-mono text-[12px] font-semibold text-text-primary">{bit.bit}</span>
            <span
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold"
              style={{
                color: positive ? 'oklch(48% 0.13 155)' : 'oklch(52% 0.16 25)',
                background: positive ? 'rgb(0 215 34 / 0.10)' : 'rgb(239 68 68 / 0.10)',
              }}
            >
              {positive ? <ArrowUp size={11} /> : <ArrowDown size={11} />}
              {positive ? 'pushes Active' : 'pushes Inactive'}
            </span>
            <span className="rounded-full bg-[rgb(8_8_8_/_0.055)] px-2 py-0.5 text-[10px] font-medium text-text-tertiary">
              {confidence}
            </span>
          </div>
          <p className="mt-1 break-all text-[12px] leading-5 text-text-secondary">{sub}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="t-mono text-[12px] font-semibold" style={{ color: positive ? 'oklch(48% 0.13 155)' : 'oklch(52% 0.16 25)' }}>
            {shap >= 0 ? '+' : ''}{shap.toFixed(5)}
          </p>
          <p className="text-[10px] text-text-disabled">SHAP</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-[1fr_auto_1fr] items-center gap-1">
        <div className="relative h-2 overflow-hidden rounded-l-full bg-[rgb(239_68_68_/_0.09)]">
          {!positive && <div className="absolute right-0 h-full rounded-l-full bg-[linear-gradient(90deg,oklch(78%_0.11_55),oklch(70%_0.16_25))]" style={{ width: `${width * 2}%` }} />}
        </div>
        <div className="h-4 w-px bg-black/25" />
        <div className="relative h-2 overflow-hidden rounded-r-full bg-[rgb(0_215_34_/_0.09)]">
          {positive && <div className="absolute left-0 h-full rounded-r-full bg-[linear-gradient(90deg,oklch(66%_0.115_155),oklch(74%_0.13_195))]" style={{ width: `${width * 2}%` }} />}
        </div>
      </div>

      {bit.molecule_substructures?.[0]?.smiles && (
        <div className="mt-3 flex items-center gap-3 rounded-md bg-white/55 p-2">
          <img
            src={moleculeImageUrl(bit.molecule_substructures[0].smiles, 112, 72)}
            alt={bit.molecule_substructures[0].smiles}
            className="h-[72px] w-[112px] shrink-0 rounded bg-white object-contain"
            loading="lazy"
            decoding="async"
          />
          <p className="min-w-0 break-all text-[11px] leading-4 text-text-tertiary">
            molecule substructure, atom {bit.molecule_substructures[0].atom_idx}, radius {bit.molecule_substructures[0].radius}
          </p>
        </div>
      )}
    </div>
  )
}

function InlinePrediction({ smiles }: { smiles: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['chat-predict', smiles],
    queryFn: () => predict(smiles),
    retry: false,
    staleTime: 300_000,
  })

  if (isLoading) {
    return (
      <div className="flex items-center gap-2.5 text-xs text-text-tertiary mb-4 pb-4 border-b border-border-subtle">
        <div className="animate-spin w-3.5 h-3.5 border border-text-disabled border-t-[var(--accent-blue-deep)] rounded-full shrink-0" />
        Running model prediction...
      </div>
    )
  }

  if (isError || !data) return null

  const isActive = data.prediction === 'Active'
  const tone = activityTone(data.probability_active)
  const topBits = data.top_bits.slice(0, 3)
  const maxAbs = Math.max(...topBits.map(bit => Math.abs(bit.shap_value)), 0.000001)

  return (
    <div className="mb-4 space-y-4 border-b border-border-subtle pb-4">
      <div className="flex items-center justify-between gap-3">
        <p className="t-label">Model prediction</p>
        <span
          className="rounded-full px-2.5 py-1 text-[11px] font-semibold"
          style={{ color: tone.color, background: tone.bg }}
        >
          {tone.label}
        </span>
      </div>

      <div className="flex items-start gap-4">
        <img
          src={moleculeImageUrl(data.canonical_smiles, 160, 100)}
          alt={data.canonical_smiles}
          className="rounded-md shrink-0"
          style={{ width: 160, height: 100, objectFit: 'contain', background: 'rgba(255,255,255,0.95)' }}
          loading="lazy"
          decoding="async"
        />
        <div className="space-y-2.5 flex-1 min-w-0 pt-1">
          <Badge variant={isActive ? 'active' : 'inactive'} className="text-xs">
            {data.prediction}
          </Badge>
          <div>
            <p className="mb-1 text-2xl font-semibold tracking-normal" style={{ color: tone.color }}>
              {(data.probability_active * 100).toFixed(1)}%
            </p>
            <ProbBar label="Active probability" value={data.probability_active} compact showPrediction={false} />
          </div>
          <p className="t-mono text-text-disabled">
            P(inactive) {(data.probability_inactive * 100).toFixed(1)}% | {data.n_on_bits} bits ON | ECFP{data.radius * 2}
          </p>
        </div>
      </div>

      <div className="grid gap-2">
        <div className="flex items-center justify-between">
          <p className="t-label">Top SHAP ECFP6 drivers</p>
          <p className="text-[10px] font-medium text-text-disabled">left suppresses, right supports activity</p>
        </div>
        {topBits.map(bit => (
          <ShapBitRow key={bit.bit} bit={bit} maxAbs={maxAbs} />
        ))}
      </div>
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({
  modelLoaded,
  onPrompt,
}: {
  modelLoaded: boolean
  onPrompt: (value: string) => void
}) {
  const prompts = [
    { label: 'Summarize dataset', value: 'Summarize the current dataset', icon: Database },
    { label: 'Explain prediction', value: 'Explain a model prediction for a molecule', icon: FlaskConical },
    { label: 'Read SHAP values', value: 'Help me interpret SHAP values', icon: BarChart3 },
  ]

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="flex size-14 items-center justify-center rounded-full border border-[rgb(255_174_19_/_0.24)] bg-[rgb(255_174_19_/_0.10)] shadow-[0_18px_40px_rgb(255_174_19_/_0.13)]">
        <Sparkles size={24} className="text-[var(--accent-yellow)]" />
      </div>
      <div className="space-y-2">
        <p className="text-2xl font-medium leading-tight text-text-primary">Ask me anything</p>
        <p className="mx-auto max-w-sm text-sm leading-6 text-text-tertiary">
          Molecules, bioactivity, SHAP values, model explanations.
        </p>
      </div>
      <div className="flex w-full flex-wrap justify-center gap-3">
        {prompts.map(({ label, value, icon: Icon }) => (
          <button
            key={label}
            type="button"
            onClick={() => onPrompt(value)}
            className="suggestion-button interactive-surface inline-flex items-center justify-start gap-3 text-left hover:border-[var(--glass-border-strong)]"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-[rgb(8_8_8_/_0.055)] text-text-primary">
              <Icon size={17} />
            </span>
            <span className="min-w-0 flex-1 text-sm font-medium leading-5 text-text-primary">{label}</span>
          </button>
        ))}
      </div>
      {modelLoaded && (
        <div className="glass rounded-md px-5 py-3">
          <p className="t-mono text-text-tertiary">predict "O=C(Nc1ccccc1)c1ccncc1"</p>
        </div>
      )}
    </div>
  )
}

// ── ChatPage ──────────────────────────────────────────────────────────────────

export function ChatPage() {
  const modelLoaded = useAppStore(s => s.modelLoaded)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send() {
    const text = input.trim()
    if (!text || streaming) return
    setInput('')

    const smiles = modelLoaded ? extractSmiles(text) : null
    setMessages(m => [...m, { id: crypto.randomUUID(), role: 'user', content: text }])
    setStreaming(true)
    setMessages(m => [...m, { id: crypto.randomUUID(), role: 'assistant', content: '', predictSmiles: smiles ?? undefined }])

    try {
      let gotChunk = false
      for await (const chunk of streamChat(text, true, smiles ?? undefined)) {
        gotChunk = true
        setMessages(m => {
          const copy = [...m]
          const last = copy[copy.length - 1]
          copy[copy.length - 1] = { ...last, content: last.content + chunk }
          return copy
        })
      }
      if (!gotChunk) {
        const fallback = await chatSimple(text, true, smiles ?? undefined)
        setMessages(m => {
          const copy = [...m]
          copy[copy.length - 1] = { ...copy[copy.length - 1], content: fallback.response }
          return copy
        })
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      setMessages(m => {
        const copy = [...m]
        copy[copy.length - 1] = { ...copy[copy.length - 1], content: `Chat unavailable: ${message}` }
        return copy
      })
    } finally {
      setStreaming(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="t-page">Chat</h1>
          <p className="t-caption mt-0.5">Ask questions about molecules, predictions, and model explanations</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        {messages.length === 0 && <EmptyState modelLoaded={modelLoaded} onPrompt={setInput} />}

        <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
        {messages.map((m, i) => (
          <div key={m.id} className={cn('flex gap-4', m.role === 'user' && 'justify-end')}>
            {m.role === 'assistant' && (
              <div className="mt-1 flex size-9 shrink-0 items-center justify-center rounded-full border border-white/70 bg-[rgb(0_215_34_/_0.14)] shadow-[0_10px_24px_rgb(8_8_8_/_0.08)] backdrop-blur-md">
                <Bot size={16} className="text-[var(--accent-green)]" />
              </div>
            )}

            <div className={cn(
              'chat-bubble max-w-[min(42rem,78vw)] transition-all duration-200',
              m.role === 'user'
                ? 'chat-bubble-user'
                : 'chat-bubble-assistant',
            )}>
              {m.role === 'assistant' && m.predictSmiles && (
                <InlinePrediction smiles={m.predictSmiles} />
              )}
              <span className="whitespace-pre-wrap">{m.content}</span>
              {streaming && i === messages.length - 1 && m.role === 'assistant' && (
                <span className="inline-block w-1.5 h-4 bg-amber-400 ml-1 animate-pulse rounded-sm" />
              )}
            </div>

            {m.role === 'user' && (
              <div className="mt-1 flex size-9 shrink-0 items-center justify-center rounded-full border border-[rgb(255_174_19_/_0.28)] bg-[rgb(255_174_19_/_0.12)] shadow-[0_10px_24px_rgb(255_174_19_/_0.13)] backdrop-blur-md">
                <User size={16} className="text-[var(--accent-yellow)]" />
              </div>
            )}
          </div>
        ))}
        </div>

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-4 md:px-8" style={{ borderTop: '1px solid var(--border-subtle)' }}>
        <div className="mx-auto flex max-w-4xl items-center gap-3">
          <textarea
            id="chat-input"
            aria-label="Chat message"
            className="chat-composer input-glass h-[4.25rem] flex-1 text-[15.5px] leading-6 text-text-primary
              placeholder:text-text-disabled resize-none overflow-hidden outline-none transition-all
              focus:border-[var(--brand-accent)] focus:shadow-[0_0_0_4px_oklch(66%_0.115_155_/_0.15),0_4px_12px_-6px_rgb(15_18_28_/_0.18)]"
            placeholder="Ask something about the dataset or the model"
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          />
          <Button
            variant="ghost"
            onClick={send}
            disabled={!input.trim() || streaming}
            size="icon-md"
            className="h-[4.25rem] w-[4.25rem] rounded-2xl border border-[oklch(48%_0.13_155_/_0.50)] bg-[linear-gradient(180deg,oklch(70%_0.13_155),oklch(58%_0.13_155))] text-white shadow-[0_1px_0_rgb(255_255_255_/_0.35)_inset,0_6px_14px_-4px_oklch(50%_0.13_155_/_0.45)] hover:scale-105 hover:text-white disabled:opacity-70"
          >
            <Send size={18} />
          </Button>
        </div>
      </div>
    </div>
  )
}
