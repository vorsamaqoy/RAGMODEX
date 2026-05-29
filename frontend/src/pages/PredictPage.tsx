import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { predict, type PredictResult, type BitInfo, type ActiveBitInfo } from '../lib/api'
import { useAppStore } from '../store'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Badge } from '../components/ui/Badge'
import { MolImage } from '../components/MolImage'
import { ProbBar } from '../components/ui/ProbBar'
import { AlertCircle } from 'lucide-react'

// ── SHAP bar chart ────────────────────────────────────────────────────────────

function ShapBarChart({ bits }: { bits: BitInfo[] }) {
  if (bits.length === 0) return null

  const barH = 30
  const PAD = { l: 72, r: 60, t: 16, b: 36 }
  const W = 480
  const H = bits.length * barH + PAD.t + PAD.b
  const pw = W - PAD.l - PAD.r

  const maxAbs = Math.max(...bits.map(b => Math.abs(b.shap_value)), 0.0001)
  const cx = PAD.l + pw / 2
  const scale = (pw / 2) / maxAbs

  const tickVals = [-maxAbs, -maxAbs / 2, 0, maxAbs / 2, maxAbs]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: H }} role="img" aria-label={`SHAP feature importance chart showing ${bits.length} fingerprint bits`}>
      {tickVals.map((v, i) => (
        <g key={i}>
          <line
            x1={cx + v * scale} x2={cx + v * scale}
            y1={PAD.t} y2={H - PAD.b}
            stroke={v === 0 ? 'rgba(8,8,8,0.18)' : 'rgba(8,8,8,0.07)'}
            strokeWidth={v === 0 ? 1.2 : 0.7}
          />
          <text x={cx + v * scale} y={H - PAD.b + 13}
            textAnchor="middle" fontSize="8.5" fill="#5a5a5a">
            {v === 0 ? '0' : (v > 0 ? '+' : '') + v.toFixed(3)}
          </text>
        </g>
      ))}
      <text x={W / 2} y={H - 3} textAnchor="middle" fontSize="10" fill="#5a5a5a">SHAP value</text>

      {bits.map((bit, i) => {
        const v = bit.shap_value
        const barW = Math.max(Math.abs(v) * scale, 1)
        const barX = v >= 0 ? cx : cx - barW
        const color = v >= 0 ? 'oklch(66% 0.115 155)' : 'oklch(70% 0.16 25)'
        const midY = PAD.t + i * barH + barH / 2

        return (
          <g key={bit.bit_index}>
            <rect x={barX} y={PAD.t + i * barH + 5}
              width={barW} height={barH - 10}
              fill={color} opacity="0.70" rx="3" />
            <text x={PAD.l - 5} y={midY + 4}
              textAnchor="end" fontSize="9.5" fill="#5a5a5a">
              {bit.bit.replace(/^ECFP\d+_/, 'bit ')}
            </text>
            <text
              x={v >= 0 ? barX + barW + 4 : barX - 4}
              y={midY + 4}
              textAnchor={v >= 0 ? 'start' : 'end'}
              fontSize="8.5" fill={color}>
              {v > 0 ? '+' : ''}{v.toFixed(4)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function collisionColor(bit: ActiveBitInfo) {
  const dominance = bit.training_info?.dominance ?? 0
  const hue = Math.max(0, Math.min(120, dominance * 1.2))
  return `hsl(${hue} 78% 45%)`
}

function BitCollisionMap({ bits }: { bits: ActiveBitInfo[] }) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  if (bits.length === 0) return null

  const selected = bits.find(b => b.bit_index === selectedIndex) ?? bits[0]
  const info = selected.training_info
  const totalSubstructures = info
    ? Object.values(info.substructures).reduce((sum, count) => sum + count, 0)
    : 0
  const substructures = info
    ? Object.entries(info.substructures).slice(0, 12)
    : []

  return (
    <Card className="col-span-1 md:col-span-3">
      <CardHeader>
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="t-subheading">Bit Collision Map</p>
            <p className="t-caption mt-0.5">
              {bits.length} active bits · color follows dominant-substructure coverage
            </p>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-text-tertiary">
            <span>mixed</span>
            <span className="h-2 w-20 rounded-sm bg-gradient-to-r from-[var(--accent-red)] via-[var(--accent-yellow)] to-[var(--accent-green)]" />
            <span>dominant</span>
          </div>
        </div>
      </CardHeader>
      <CardBody className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,24rem)]">
        <div className="flex max-h-[22rem] flex-wrap content-start gap-1.5 overflow-y-auto pr-1">
          {bits.map(bit => {
            const active = bit.bit_index === selected.bit_index
            const dominance = bit.training_info?.dominance ?? 0
            const unique = bit.training_info?.n_unique_substructures ?? 0
            return (
              <button
                key={bit.bit_index}
                type="button"
                title={`${bit.bit} · ${unique || 'no'} substructures · dominant ${dominance.toFixed(1)}%`}
                onClick={() => setSelectedIndex(bit.bit_index)}
                className="h-8 min-w-12 rounded-md border px-2 font-mono text-[11px] font-semibold text-white shadow-[0_8px_18px_rgb(8_8_8_/_0.10)] transition-all hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue-deep)]/30"
                style={{
                  backgroundColor: collisionColor(bit),
                  borderColor: active ? 'rgba(8,8,8,0.46)' : 'rgba(255,255,255,0.72)',
                  boxShadow: active ? '0 0 0 2px rgb(8 8 8 / 0.16), 0 14px 28px rgb(8 8 8 / 0.16)' : undefined,
                }}
              >
                {bit.bit_index}
              </button>
            )
          })}
        </div>

        <div className="rounded-md border border-white/70 bg-white/65 p-4 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.78)]">
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <p className="t-label">{selected.bit}</p>
              <p className="t-caption mt-1">
                {info
                  ? `${info.n_unique_substructures} substructures · dominant ${info.dominance.toFixed(1)}%`
                  : 'No training collision data for this bit'}
              </p>
            </div>
            {info && (
              <Badge variant={info.dominance >= 70 ? 'active' : info.dominance >= 45 ? 'warn' : 'inactive'}>
                {info.is_ambiguous ? 'collision' : 'unique'}
              </Badge>
            )}
          </div>

          {info ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <MetaRow label="Active ratio" value={`${(info.active_ratio * 100).toFixed(1)}%`} />
                <MetaRow label="Activations" value={info.total_activations} />
              </div>
              <div className="space-y-2">
                {substructures.map(([smiles, count]) => {
                  const pct = totalSubstructures > 0 ? (count / totalSubstructures) * 100 : 0
                  return (
                    <div key={smiles} className="rounded-md border border-white/70 bg-white/70 px-3 py-2">
                      <div className="mb-1.5 flex items-center justify-between gap-3">
                        <span className="truncate font-mono text-[11px] text-text-secondary">{smiles}</span>
                        <span className="t-mono shrink-0 text-text-tertiary">{pct.toFixed(1)}%</span>
                      </div>
                      <div className="h-1.5 rounded-sm bg-bg-inset">
                        <div
                          className="h-full rounded-sm bg-[var(--accent-blue-deep)]"
                          style={{ width: `${Math.max(2, pct)}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-text-tertiary">Substructures in this molecule:</p>
              {selected.molecule_substructures.length > 0 ? selected.molecule_substructures.map(sub => (
                <div key={`${sub.smiles}-${sub.atom_idx}-${sub.radius}`} className="rounded-md border border-white/70 bg-white/70 px-3 py-2 font-mono text-[11px] text-text-secondary">
                  {sub.smiles} · atom {sub.atom_idx} · r{sub.radius}
                </div>
              )) : (
                <p className="text-sm text-text-tertiary">No extractable substructure for this active bit.</p>
              )}
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function PredictPage() {
  const modelLoaded = useAppStore(s => s.modelLoaded)
  const [smiles, setSmiles] = useState('')
  const [result, setResult] = useState<PredictResult | null>(null)

  const mut = useMutation({
    mutationFn: () => predict(smiles),
    onSuccess: setResult,
  })

  const shap = result?.top_bits ?? []

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="t-page">Bioactivity Prediction</h1>
          <p className="t-caption mt-0.5">Configurable ECFP fingerprint · SHAP feature importance</p>
        </div>
      </div>

      <div className="page-content max-w-5xl space-y-6">
        {!modelLoaded && (
          <div className="status-notice status-notice-warning">
            <AlertCircle size={16} className="shrink-0" />
            No model loaded — go to Settings to upload a model.
          </div>
        )}

        {/* SMILES input */}
        <Card>
          <CardBody className="flex flex-col gap-4 md:flex-row md:items-center">
            <Input
              placeholder="Enter SMILES string…  e.g. CC(=O)Oc1ccccc1C(=O)O"
              value={smiles}
              onChange={e => setSmiles(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && smiles && mut.mutate()}
              className="font-mono md:flex-1"
            />
            <Button
              disabled={!smiles || !modelLoaded}
              loading={mut.isPending}
              onClick={() => mut.mutate()}
            >
              Predict
            </Button>
          </CardBody>
        </Card>

        {mut.error && (
          <div className="status-notice status-notice-error">
            <AlertCircle size={15} className="shrink-0" />{String(mut.error)}
          </div>
        )}

        {result && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Molecule + result */}
            <div className="col-span-1 space-y-5">
              <Card>
                <CardBody className="flex flex-col items-center gap-4">
                  <MolImage smiles={result.canonical_smiles} width={260} height={180} className="rounded-md" />
                  <Badge
                    variant={result.prediction === 'Active' ? 'active' : 'inactive'}
                    className="px-5 py-2.5 text-sm"
                  >
                    {result.prediction}
                  </Badge>
                  <div className="w-full">
                    <ProbBar value={result.probability_active} />
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardHeader>
                  <p className="t-label">Fingerprint details</p>
                </CardHeader>
                <CardBody className="space-y-2">
                  <MetaRow label="Bits ON"    value={result.n_on_bits} />
                  <MetaRow label="Total bits" value={result.n_bits} />
                  <MetaRow label="FP radius"  value={result.radius} />
                  <MetaRow label="Baseline"   value={result.expected_value.toFixed(4)} />
                </CardBody>
              </Card>
            </div>

            {/* SHAP chart */}
            <Card className="col-span-1 md:col-span-2">
              <CardHeader>
                <p className="t-subheading">SHAP Feature Importance</p>
                <p className="t-caption mt-0.5">Top {shap.length} most influential fingerprint bits</p>
              </CardHeader>
              <CardBody>
                <ShapBarChart bits={shap} />
              </CardBody>
            </Card>

            <BitCollisionMap bits={result.active_bits ?? []} />

            {/* Bit table */}
            <Card className="col-span-1 md:col-span-3">
              <CardHeader>
                <p className="t-subheading">Bit Details</p>
              </CardHeader>
              <CardBody>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}
                        className="text-left">
                        <th className="pb-3 pr-4 t-label">#</th>
                        <th className="pb-3 pr-4 t-label">Bit</th>
                        <th className="pb-3 pr-4 t-label">SHAP</th>
                        <th className="pb-3 pr-4 t-label">Direction</th>
                        <th className="pb-3 t-label">Substructure</th>
                      </tr>
                    </thead>
                    <tbody>
                      {shap.map(b => (
                        <tr key={b.bit_index}
                          className="hover:bg-white/[0.02] transition-colors"
                          style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                          <td className="py-3 pr-4 text-text-tertiary">{b.rank}</td>
                          <td className="py-3 pr-4 font-mono text-text-secondary">{b.bit}</td>
                          <td className={`py-3 pr-4 font-mono font-semibold ${b.shap_value > 0 ? 'text-[var(--accent-green)]' : 'text-[var(--accent-red)]'}`}>
                            {b.shap_value > 0 ? '+' : ''}{b.shap_value.toFixed(5)}
                          </td>
                          <td className="py-3 pr-4">
                            <Badge variant={b.shap_value > 0 ? 'active' : 'inactive'}>{b.direction}</Badge>
                          </td>
                          <td className="py-3 text-text-secondary font-mono text-[11px]">
                            {b.molecule_substructures[0]?.smiles ?? (b.bit_on ? '—' : 'bit OFF')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardBody>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}

function MetaRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-white/70 bg-white/55 px-4 py-3 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.72)]">
      <span className="t-caption">{label}</span>
      <span className="t-mono text-text-secondary">{value}</span>
    </div>
  )
}
