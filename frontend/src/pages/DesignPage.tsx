import { Fragment, useState, useCallback, useRef } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import type { ReactElement } from 'react'
import { toast } from 'sonner'
import {
  runDesign,
  predict,
  moleculeImageUrl,
  getMoleculeDiff,
  type DesignCandidate,
  type HistoryStep,
} from '../lib/api'
import { useAppStore } from '../store'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Badge } from '../components/ui/Badge'
import { ProbBar } from '../components/ui/ProbBar'
import { Tooltip, TooltipContent, TooltipTrigger } from '../components/shadcn/tooltip'
import { AlertCircle, TrendingUp, TrendingDown, Copy, RefreshCw, HelpCircle } from 'lucide-react'

// ── helpers ───────────────────────────────────────────────────────────────────

function pct(v: number) { return `${(v * 100).toFixed(1)}%` }
function deltaPct(v: number) { return `${v > 0 ? '+' : ''}${(v * 100).toFixed(1)}%` }

// ── NumInput ──────────────────────────────────────────────────────────────────

function NumInput({
  label, hint, value, onChange, min, max, step = 1,
}: {
  label: string; hint?: string; value: number; onChange: (v: number) => void
  min?: number; max?: number; step?: number
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <label className="t-label">{label}</label>
        {hint && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button type="button" tabIndex={-1} className="flex size-6 items-center justify-center rounded-md text-text-tertiary transition-colors hover:bg-white/60 hover:text-text-primary">
                <HelpCircle size={12} />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-[220px] text-xs leading-relaxed">
              {hint}
            </TooltipContent>
          </Tooltip>
        )}
      </div>
      <input
        type="number" min={min} max={max} step={step} value={value}
        onChange={e => { const v = parseInt(e.target.value, 10); if (!isNaN(v)) onChange(v) }}
        className="h-10 min-h-10 w-full rounded-xl border border-border-subtle bg-white/55 px-3 py-2 font-mono text-sm text-text-primary shadow-[inset_0_1px_0_rgb(255_255_255_/_0.70)] outline-none transition-colors focus:border-[var(--brand-accent)] focus:ring-2 focus:ring-[oklch(66%_0.115_155_/_0.15)]"
      />
    </div>
  )
}

// ── TernaryWeights ────────────────────────────────────────────────────────────
// Vertices in SVG space (viewBox 0 0 280 248):
//   A = Activity  (bottom-left)
//   B = Diversity (bottom-right)
//   C = AD Score  (top-center)

const TA = { x: 28, y: 210 }
const TB = { x: 252, y: 210 }
const TC = { x: 140, y: 16 }

function weightsToPos(wA: number, wB: number, wC: number) {
  return {
    x: wA * TA.x + wB * TB.x + wC * TC.x,
    y: wA * TA.y + wB * TB.y + wC * TC.y,
  }
}

function posToWeights(px: number, py: number): [number, number, number] {
  const wC = Math.max(0, Math.min(1, (TA.y - py) / (TA.y - TC.y)))
  const xL = TA.x + wC * (TC.x - TA.x)
  const xR = TB.x + wC * (TC.x - TB.x)
  const rowFrac = xR === xL ? 0.5 : Math.max(0, Math.min(1, (px - xL) / (xR - xL)))
  const rem = 1 - wC
  return [rem * (1 - rowFrac), rem * rowFrac, wC]
}

function snapWeights(wA: number, wB: number, wC: number): [number, number, number] {
  const N = 20
  let i = Math.round(wA * N)
  let j = Math.round(wB * N)
  let k = Math.round(wC * N)
  const diff = N - (i + j + k)
  if (diff !== 0) {
    if (i >= j && i >= k) i += diff
    else if (j >= k) j += diff
    else k += diff
  }
  return [Math.max(0, i) / N, Math.max(0, j) / N, Math.max(0, k) / N]
}

const PRESETS: [string, number, number, number][] = [
  ['Activity', 0.80, 0.10, 0.10],
  ['Balanced', 0.50, 0.25, 0.25],
  ['Diversity', 0.10, 0.80, 0.10],
]

function TernaryWeights({
  wActivity, wDiversity, wAd, locked, onChange,
}: {
  wActivity: number; wDiversity: number; wAd: number
  locked?: boolean
  onChange: (wA: number, wB: number, wC: number) => void
}) {
  const svgRef = useRef<SVGSVGElement>(null)
  const dragging = useRef(false)
  const pos = weightsToPos(wActivity, wDiversity, wAd)

  function applyEvent(e: React.PointerEvent | PointerEvent) {
    if (!svgRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    const px = ((e as PointerEvent).clientX - rect.left) * (280 / rect.width)
    const py = ((e as PointerEvent).clientY - rect.top) * (248 / rect.height)
    let [wA, wB, wC] = posToWeights(px, py)
    if (locked) { const s = wA + wB || 1; wA /= s; wB /= s; wC = 0 }
    const [sA, sB, sC] = snapWeights(wA, wB, wC)
    onChange(sA, sB, sC)
  }

  const onDown = (e: React.PointerEvent<SVGSVGElement>) => {
    dragging.current = true
    svgRef.current?.setPointerCapture(e.pointerId)
    applyEvent(e)
  }
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => { if (dragging.current) applyEvent(e) }
  const onUp = () => { dragging.current = false }

  // Grid lines at 0.1 step (9 per direction)
  const gridLines: ReactElement[] = []
  for (let s = 1; s < 10; s++) {
    const t = s / 10
    // Constant wC (parallel to AB)
    gridLines.push(<line key={`c${s}`}
      x1={TA.x + t * (TC.x - TA.x)} y1={TA.y + t * (TC.y - TA.y)}
      x2={TB.x + t * (TC.x - TB.x)} y2={TB.y + t * (TC.y - TB.y)}
      stroke="rgba(8,8,8,0.07)" strokeWidth="0.8" />)
    // Constant wA (parallel to BC)
    gridLines.push(<line key={`a${s}`}
      x1={t * TA.x + (1 - t) * TB.x} y1={t * TA.y + (1 - t) * TB.y}
      x2={t * TA.x + (1 - t) * TC.x} y2={t * TA.y + (1 - t) * TC.y}
      stroke="rgba(8,8,8,0.07)" strokeWidth="0.8" />)
    // Constant wB (parallel to AC)
    gridLines.push(<line key={`b${s}`}
      x1={(1 - t) * TA.x + t * TB.x} y1={(1 - t) * TA.y + t * TB.y}
      x2={t * TB.x + (1 - t) * TC.x} y2={t * TB.y + (1 - t) * TC.y}
      stroke="rgba(8,8,8,0.07)" strokeWidth="0.8" />)
  }

  return (
    <div className="space-y-2">
      <span className="t-label">MMR Weights</span>
      <svg
        ref={svgRef}
        viewBox="0 0 280 248"
        className="mx-auto w-full max-w-[148px] cursor-crosshair select-none"
        style={{ touchAction: 'none' }}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
      >
        {gridLines}
        <polygon points={`${TA.x},${TA.y} ${TB.x},${TB.y} ${TC.x},${TC.y}`}
          fill="rgb(255 255 255 / 0.50)" stroke="rgb(15 18 28 / 0.18)" strokeWidth="1.5" />

        {/* vertex labels */}
        <text x={TA.x} y={TA.y + 16} textAnchor="middle" fontSize="10" fill="#6b6f7a">Activity</text>
        <text x={TB.x} y={TB.y + 16} textAnchor="middle" fontSize="10" fill="#6b6f7a">Diversity</text>
        <text x={TC.x} y={TC.y - 7} textAnchor="middle" fontSize="10"
          fill={locked ? '#9ea3ad' : '#6b6f7a'}>AD Score{locked ? ' (locked)' : ''}</text>

        {/* current weight values near each vertex */}
        <text x={TA.x} y={TA.y + 30} textAnchor="middle" fontSize="9" fill="oklch(38% 0.085 155)" fontFamily="monospace">
          {(wActivity * 100).toFixed(0)}%
        </text>
        <text x={TB.x} y={TB.y + 30} textAnchor="middle" fontSize="9" fill="oklch(38% 0.085 240)" fontFamily="monospace">
          {(wDiversity * 100).toFixed(0)}%
        </text>
        <text x={TC.x} y={TC.y + 22} textAnchor="middle" fontSize="9"
          fill={locked ? '#9ea3ad' : 'oklch(38% 0.085 155)'} fontFamily="monospace">
          {(wAd * 100).toFixed(0)}%
        </text>

        {/* position indicator */}
        <circle cx={pos.x} cy={pos.y} r="10" fill="oklch(66% 0.115 155)" fillOpacity="0.18" />
        <circle cx={pos.x} cy={pos.y} r="5.5" fill="oklch(60% 0.13 155)" stroke="white" strokeWidth="1.5" />
      </svg>

      {(() => {
        const activePreset = PRESETS.find(([, wa, wd, wad]) => {
          let fa = wa, fd = wd, fc = wad
          if (locked) { const s = fa + fd || 1; fa /= s; fd /= s; fc = 0 }
          const [sA, sB, sC] = snapWeights(fa, fd, fc)
          return Math.abs(sA - wActivity) < 0.001 && Math.abs(sB - wDiversity) < 0.001 && Math.abs(sC - wAd) < 0.001
        })?.[0] ?? ''

        return (
          <div className="grid grid-cols-3 gap-1">
            {PRESETS.map(([label]) => (
              <button
                key={label}
                type="button"
                aria-pressed={activePreset === label}
                onClick={() => {
                  const val = label
                  const preset = PRESETS.find(([l]) => l === val)
                  if (!preset) return
                  let [, fa, fd, fc] = preset
                  if (locked) { const s = fa + fd || 1; fa /= s; fd /= s; fc = 0 }
                  const [sA, sB, sC] = snapWeights(fa, fd, fc)
                  onChange(sA, sB, sC)
                }}
                className={`h-8 rounded-md border px-2 text-[11px] font-semibold transition-colors
                  ${activePreset === label
                    ? 'border-[oklch(66%_0.115_155_/_0.35)] bg-[oklch(92%_0.04_155_/_0.70)] text-[var(--brand-accent)]'
                    : 'border-border-subtle bg-white/55 text-text-tertiary hover:bg-white/80 hover:text-text-primary'}`}
              >
                {label}
              </button>
            ))}
          </div>
        )
      })()}
    </div>
  )
}

// ── SettingsPanel ─────────────────────────────────────────────────────────────

interface Settings {
  nIterations: number
  beamSize: number
  topK: number
  patience: number
  useDruglikeness: boolean
  wActivity: number
  wDiversity: number
  wAd: number
}

function SettingsPanel({
  settings, onChange, lockAd,
}: {
  settings: Settings; onChange: (s: Settings) => void; lockAd: boolean
}) {
  const s = settings
  const set = useCallback(
    (patch: Partial<Settings>) => onChange({ ...s, ...patch }),
    [s, onChange],
  )

  return (
    <section className="mt-4 border-t border-border-subtle pt-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="t-subheading text-base">Generation settings</p>
          <p className="t-caption mt-0.5">Beam search, result count, and ranking balance.</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_212px]">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-x-3 gap-y-3">
            <NumInput label="Iterations" value={s.nIterations}
              hint="Number of beam-search rounds. More = deeper exploration but longer runtime."
              onChange={v => set({ nIterations: Math.min(10, Math.max(2, v)) })} min={2} max={10} />
            <NumInput label="Beam size" value={s.beamSize}
              hint="Candidates kept per iteration. Higher = more diverse search, slower execution."
              onChange={v => set({ beamSize: Math.min(20, Math.max(1, v)) })} min={1} max={20} />
            <NumInput label="Top results" value={s.topK}
              hint="Final candidates to return. Must be a multiple of 3 (max 18)."
              onChange={v => set({ topK: Math.min(18, Math.max(3, v)) })} min={3} max={18} step={3} />
            <NumInput label="Patience" value={s.patience}
              hint="Stop early if no improvement is found after this many consecutive iterations."
              onChange={v => set({ patience: Math.min(6, Math.max(1, v)) })} min={1} max={6} />
          </div>

          <div className="flex h-11 items-center gap-3 rounded-xl border border-border-subtle bg-white/55 px-3 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.70)]">
            <button
              type="button"
              role="switch"
              aria-checked={s.useDruglikeness}
              onClick={() => set({ useDruglikeness: !s.useDruglikeness })}
              className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgb(232_200_120_/_0.30)] focus-visible:ring-offset-1 focus-visible:ring-offset-transparent
                ${s.useDruglikeness ? 'bg-[var(--brand-accent)]' : 'bg-[rgb(15_18_28_/_0.15)]'}`}
            >
              <span className={`inline-block size-3.5 transform rounded-full bg-white shadow transition-transform ${s.useDruglikeness ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="cursor-default text-sm font-medium text-text-secondary transition-colors hover:text-text-primary">
                  Drug-likeness filter
                </span>
              </TooltipTrigger>
              <TooltipContent className="max-w-[240px] text-xs leading-relaxed">
                Lipinski-extended filter: MW, logP, HBD/HBA, TPSA, and rotatable bonds.
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        <div className="rounded-2xl border border-border-subtle bg-white/45 px-3 py-3 lg:border-l">
          <TernaryWeights
            wActivity={s.wActivity}
            wDiversity={s.wDiversity}
            wAd={s.wAd}
            locked={lockAd}
            onChange={(wa, wd, wad) => set({ wActivity: wa, wDiversity: wd, wAd: wad })}
          />
        </div>
      </div>
    </section>
  )
}

// ── CandidateCard ─────────────────────────────────────────────────────────────

function CandidateCard({
  candidate: c, selected, onClick,
}: {
  candidate: DesignCandidate; selected: boolean; onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`liquid-panel interactive-surface w-full p-5 text-left transition-all
        ${selected
          ? 'border-[oklch(66%_0.115_155_/_0.36)] bg-[oklch(92%_0.04_155_/_0.64)] shadow-[0_20px_46px_oklch(50%_0.13_155_/_0.12)]'
          : 'hover:border-[var(--glass-border-strong)] hover:bg-white/70'}`}
    >
      <div className="relative">
        <img src={moleculeImageUrl(c.smiles, 200, 130)} alt={c.smiles}
          width={200} height={130} loading="lazy" decoding="async"
          className="mb-4 w-full rounded-md bg-white" style={{ objectFit: 'contain' }} />
        <span className="absolute left-2 top-2 rounded-full border border-white/70 bg-white/78 px-3 py-1.5 text-[11px] font-bold text-text-primary shadow-sm backdrop-blur-sm">#{c.rank}</span>
      </div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <Badge variant={c.delta >= 0 ? 'active' : 'inactive'} className="gap-0.5">
          {c.delta >= 0 ? <TrendingUp size={10} className="shrink-0" /> : <TrendingDown size={10} className="shrink-0" />}
          {deltaPct(c.delta)}
        </Badge>
        <span className="rounded-full border border-white/70 bg-white/64 px-3.5 py-2 font-mono text-xs tabular-nums text-text-secondary shadow-sm">{pct(c.probability)}</span>
      </div>
      <div className="mb-3">
        <ProbBar value={c.probability} compact showPrediction={false} />
      </div>
      <p className="text-xs text-text-tertiary truncate font-mono leading-relaxed">
        {c.transformation || c.source}
      </p>
    </button>
  )
}

// ── DetailPanel ───────────────────────────────────────────────────────────────

function Row({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex justify-between gap-4 rounded-xl border border-border-subtle bg-white/55 px-4 py-3">
      <span className="text-text-tertiary shrink-0">{label}</span>
      <span className={`font-mono text-right break-all ${valueClass ?? 'text-text-secondary'}`}>{value}</span>
    </div>
  )
}

function DetailPanel({
  candidate: c, onUseAsBase,
}: {
  candidate: DesignCandidate; onUseAsBase: (smiles: string) => void
}) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(c.smiles).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <Card>
      <CardHeader>
        <p className="t-subheading">Selected variant</p>
      </CardHeader>
      <CardBody className="space-y-4">
        <img src={moleculeImageUrl(c.smiles, 240, 160)} alt={c.smiles}
          loading="lazy" decoding="async"
          className="rounded-lg w-full bg-white" style={{ objectFit: 'contain', height: 160 }} />
        <ProbBar value={c.probability} />
        <div className="space-y-2.5 text-xs">
          <Row label="Δ vs base" value={deltaPct(c.delta)}
            valueClass={c.delta >= 0 ? 'text-[var(--accent-green)]' : 'text-[var(--accent-red)]'} />
          <Row label="AD score" value={c.ad_score.toFixed(3)} />
          <Row label="Source" value={c.source} />
          <Row label="Iteration" value={String(c.iteration)} />
        </div>
        <p className="text-xs text-text-tertiary leading-relaxed">{c.transformation || '—'}</p>
        <div className="rounded-xl border border-border-subtle bg-white/55 p-4">
          <p className="text-[11px] font-mono text-text-secondary break-all leading-relaxed select-all">{c.smiles}</p>
        </div>
        <div className="space-y-2">
          <Button variant="secondary" size="sm" className="w-full" onClick={handleCopy}>
            <Copy size={12} />{copied ? 'Copied!' : 'Copy SMILES'}
          </Button>
          <Button variant="ghost" size="sm" className="w-full" onClick={() => onUseAsBase(c.smiles)}>
            <RefreshCw size={12} />Use as base molecule
          </Button>
        </div>
      </CardBody>
    </Card>
  )
}

// ── BasePreviewCard ───────────────────────────────────────────────────────────

function BasePreviewCard({ smiles }: { smiles: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['base-preview', smiles],
    queryFn: () => predict(smiles),
    enabled: smiles.length > 4,
    retry: false,
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="status-notice text-text-tertiary">
        <div className="animate-spin w-3.5 h-3.5 border border-text-disabled border-t-transparent rounded-full" />
        Predicting…
      </div>
    )
  }
  if (isError || !data) return null

  const prob = data.probability_active
  const isActive = data.prediction === 'Active'
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-border-subtle bg-white/50 px-4 py-3">
      <img src={moleculeImageUrl(smiles, 200, 120)} alt="Base molecule"
        loading="lazy" decoding="async"
        className="shrink-0 rounded-md bg-white shadow-sm" style={{ width: 104, height: 66, objectFit: 'contain' }} />
      <div className="min-w-0 flex-1">
        <p className="t-label mb-1">Base molecule</p>
        <p className={`text-xl font-bold tabular-nums ${isActive ? 'text-[var(--accent-green)]' : 'text-[var(--accent-red)]'}`}>
          {pct(prob)}
        </p>
        <Badge variant={isActive ? 'active' : 'inactive'} className="mt-1">{data.prediction}</Badge>
        <div className="mt-2 max-w-sm">
          <ProbBar value={prob} compact showPrediction={false} />
        </div>
      </div>
    </div>
  )
}

// ── DiffBadge ─────────────────────────────────────────────────────────────────

function DiffBadge({ smiA, smiB }: { smiA: string; smiB: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['mol-diff', smiA, smiB],
    queryFn: () => getMoleculeDiff(smiA, smiB),
    staleTime: Infinity,
    retry: false,
  })

  if (isLoading) return <div className="text-text-disabled text-lg px-2">→</div>

  if (!data || data.scaffold_change) {
    return (
      <div className="flex flex-col items-center gap-1 px-3">
        <span className="text-[10px] text-text-disabled">scaffold</span>
        <span className="text-text-tertiary text-lg">→</span>
        <span className="text-[10px] text-text-disabled">change</span>
      </div>
    )
  }

  const added = data.added_frags.slice(0, 2)
  const removed = data.removed_frags.slice(0, 2)

  return (
    <div className="flex flex-col items-center justify-center gap-1 px-1 min-w-[70px]">
      {added.map(smi => (
        <div key={smi} className="flex items-center gap-0.5">
          <span className="text-[var(--accent-green)] text-[10px] font-bold leading-none">+</span>
          <img src={moleculeImageUrl(smi, 52, 36)} alt={smi}
            loading="lazy" decoding="async"
            className="bg-white rounded" style={{ width: 52, height: 36, objectFit: 'contain' }} />
        </div>
      ))}
      <span className="text-text-tertiary text-base leading-none">→</span>
      {removed.map(smi => (
        <div key={smi} className="flex items-center gap-0.5">
          <span className="text-[var(--accent-red)] text-[10px] font-bold leading-none">−</span>
          <img src={moleculeImageUrl(smi, 52, 36)} alt={smi}
            loading="lazy" decoding="async"
            className="bg-white rounded" style={{ width: 52, height: 36, objectFit: 'contain' }} />
        </div>
      ))}
    </div>
  )
}

// ── EvolutionTimeline ─────────────────────────────────────────────────────────

function EvolutionTimeline({
  timeline, baseSMILES, baseProb, onUseAsBase,
}: {
  timeline: HistoryStep[]
  baseSMILES: string
  baseProb: number
  onUseAsBase: (smiles: string) => void
}) {
  if (timeline.length === 0) return null

  const base: HistoryStep = { iteration: 0, best_smiles: baseSMILES, best_prob: baseProb, ad_score: 0, n_generated: 0 }
  const steps = [base, ...timeline]

  return (
    <Card>
      <CardHeader>
        <p className="t-subheading">Evolution path</p>
        <p className="t-caption mt-1">
          Molecular transformations from base to top candidate
        </p>
      </CardHeader>
      <CardBody>
        <div className="overflow-x-auto pb-1">
          <div className="flex items-center gap-2 min-w-max">
            {steps.map((step, i) => (
              <Fragment key={i}>
                <div className="flex flex-col items-center gap-1.5 min-w-[130px]">
                  <span className="text-[10px] text-text-tertiary font-mono">
                    {i === 0 ? 'Base' : `Iter ${step.iteration}`}
                  </span>
                  <img
                    src={moleculeImageUrl(step.best_smiles, 130, 86)}
                    alt={step.best_smiles}
                    loading="lazy" decoding="async"
                    className="rounded-md border border-[rgb(232_200_120_/_0.18)] bg-white shadow-sm"
                    style={{ width: 130, height: 86, objectFit: 'contain' }}
                  />
                  <p className="text-[11px] font-mono font-semibold text-[var(--accent-orange)]">
                    P = {(step.best_prob * 100).toFixed(1)}%
                  </p>
                  {step.ad_score > 0 && (
                    <p className="text-[10px] font-mono text-text-tertiary">
                      AD = {step.ad_score.toFixed(2)}
                    </p>
                  )}
                  {i > 0 && (
                    <button
                      onClick={() => onUseAsBase(step.best_smiles)}
                      className="rounded-full px-3 py-1.5 text-[10px] font-medium text-text-tertiary transition-colors hover:bg-white/70 hover:text-text-primary"
                    >
                      Use as base
                    </button>
                  )}
                </div>
                {i < steps.length - 1 && (
                  <DiffBadge smiA={step.best_smiles} smiB={steps[i + 1].best_smiles} />
                )}
              </Fragment>
            ))}
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

// ── DesignPage ────────────────────────────────────────────────────────────────

const DEFAULT_SETTINGS: Settings = {
  nIterations: 5,
  beamSize: 3,
  topK: 9,
  patience: 3,
  useDruglikeness: true,
  wActivity: 0.50,
  wDiversity: 0.25,
  wAd: 0.25,
}

export function DesignPage() {
  const modelLoaded = useAppStore(s => s.modelLoaded)
  const trainingData = useAppStore(s => s.trainingData)

  const [smiles, setSmiles] = useState('')
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)
  const [selected, setSelected] = useState<DesignCandidate | null>(null)
  const [previewSmiles, setPreviewSmiles] = useState('')
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleSmilesChange = (val: string) => {
    setSmiles(val)
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => setPreviewSmiles(val.trim()), 600)
  }

  const mut = useMutation({
    mutationFn: () => {
      const s = settings
      const ws = s.wActivity + s.wDiversity + s.wAd
      const wa  = ws > 0 ? s.wActivity  / ws : 0.50
      const wd  = ws > 0 ? s.wDiversity / ws : 0.25
      const wad = ws > 0 ? s.wAd        / ws : 0.25
      return runDesign(smiles, 200, s.topK, wa, wd, wad, s.nIterations, s.beamSize, 100, s.patience, s.useDruglikeness)
    },
    onSuccess: (data) => {
      setSelected(null)
      const n = data.candidates.length
      toast.success(n > 0 ? `${n} candidate${n > 1 ? 's' : ''} generated` : 'Design complete — no candidates found')
    },
    onError: (err) => {
      toast.error(String(err))
    },
  })

  const handleUseAsBase = (newSmiles: string) => {
    setSmiles(newSmiles)
    setPreviewSmiles(newSmiles)
    setSelected(null)
    mut.reset()
  }

  const candidates = mut.data?.candidates ?? []
  const timeline   = mut.data?.timeline_path ?? []
  const hasResults = mut.isSuccess && candidates.length > 0

  return (
    <div className="flex flex-col h-full">
      <div className="px-8 py-4 backdrop-blur-xl">
        <h1 className="text-3xl font-bold tracking-normal text-text-primary">Molecular Design</h1>
        <p className="mt-0.5 text-sm font-medium text-text-tertiary">
          Beam-search optimisation maximising P(active) with structural diversity control
        </p>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-8 py-5">
      {!modelLoaded && (
        <div className="status-notice status-notice-warning">
          <AlertCircle size={16} className="shrink-0" />
          No model loaded — upload a model in Settings to enable design.
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-4 items-start">
        {/* ── left column ── */}
        <div className="space-y-4">
          <Card>
            <CardBody className="px-5 py-4 md:px-6 md:py-5">
              <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
                <label className="block space-y-1.5">
                  <span className="t-label">Base molecule SMILES</span>
                  <Input
                    placeholder="O=C(Nc1cnn(Cc2ccccc2)c1)c1ccnc2ccccc12"
                    value={smiles}
                    onChange={e => handleSmilesChange(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && smiles && modelLoaded) mut.mutate() }}
                    className="!min-h-11 !rounded-md !py-2 !shadow-none h-11 font-mono"
                  />
                </label>
                <Button disabled={!smiles || !modelLoaded} loading={mut.isPending} size="sm"
                  onClick={() => mut.mutate()} className="h-11 shrink-0 px-5">
                  {mut.isPending ? 'Running…' : 'Run Design'}
                </Button>
              </div>

              {previewSmiles.length > 4 && (
                <div className="mt-4">
                  <BasePreviewCard smiles={previewSmiles} />
                </div>
              )}

              <SettingsPanel settings={settings} onChange={setSettings} lockAd={!trainingData} />
            </CardBody>
          </Card>

          {mut.isError && (
            <div className="status-notice status-notice-error">
              <AlertCircle size={15} className="shrink-0" />{String(mut.error)}
            </div>
          )}

          {hasResults && (
            <div className="space-y-3">
              {/* summary bar */}
              <div className="liquid-panel flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-4 text-sm text-text-secondary">
                <span>Base:&nbsp;<strong className="text-text-primary tabular-nums">{pct(mut.data!.base_probability)}</strong></span>
                <span className="text-text-disabled">→</span>
                <span>Best:&nbsp;<strong className="text-[var(--accent-green)] tabular-nums">{candidates.length > 0 ? pct(candidates[0].probability) : '—'}</strong></span>
                <span className="text-text-disabled">|</span>
                <span>{mut.data!.n_valid} valid&nbsp;/&nbsp;{mut.data!.n_generated} generated</span>
              </div>

              {/* candidate grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {candidates.map(c => (
                  <CandidateCard
                    key={c.smiles}
                    candidate={c}
                    selected={selected?.smiles === c.smiles}
                    onClick={() => setSelected(prev => prev?.smiles === c.smiles ? null : c)}
                  />
                ))}
              </div>

              {/* evolution timeline */}
              <EvolutionTimeline
                timeline={timeline}
                baseSMILES={mut.data!.base_smiles}
                baseProb={mut.data!.base_probability}
                onUseAsBase={handleUseAsBase}
              />
            </div>
          )}

          {mut.isSuccess && candidates.length === 0 && (
            <div className="liquid-panel px-6 py-8 text-center text-sm text-text-tertiary">
              No candidates were generated. Try a different SMILES or adjust settings.
            </div>
          )}
        </div>

        {/* ── right column: detail panel ── */}
        <div className="xl:sticky top-6">
          {selected && mut.data ? (
            <DetailPanel
              candidate={selected}
              onUseAsBase={handleUseAsBase}
            />
          ) : (
            <div className="liquid-panel px-6 py-10 text-center text-sm text-text-tertiary">
              {hasResults ? 'Click a variant to inspect it' : 'Run design to see candidates'}
            </div>
          )}
        </div>
      </div>
      </div>
    </div>
  )
}
