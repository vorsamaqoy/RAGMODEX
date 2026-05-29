import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertCircle } from 'lucide-react'
import { getVisualizerData, moleculeImageUrl, type VisualizerMolecule } from '../lib/api'
import { useAppStore } from '../store'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Pagination } from '../components/ui/Pagination'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts'

// ── Histogram (interactive) ───────────────────────────────────────────────────

function HistTooltip({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ name: string; value: number; fill: string }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="glass space-y-1 rounded-md px-4 py-3 text-xs font-mono">
      <div className="mb-1 text-text-tertiary">P(active) ~= {Number(label).toFixed(2)}</div>
      {payload.map(p => (
        <div key={p.name} className="flex gap-2 items-center">
          <span className="inline-block w-2 h-2 rounded-sm shrink-0" style={{ background: p.fill }} />
          <span className="text-text-tertiary">{p.name}:</span>
          <span className="text-text-primary">{p.value}</span>
        </div>
      ))}
    </div>
  )
}

function Histogram({ bins, active, inactive }: {
  bins: number[]; active: number[]; inactive: number[]
}) {
  const data = bins.map((b, i) => ({
    bin: b.toFixed(2),
    Active: active[i],
    Inactive: inactive[i],
  }))

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} barCategoryGap="15%" margin={{ top: 4, right: 8, left: -16, bottom: 20 }}>
        <CartesianGrid strokeDasharray="2 4" stroke="rgba(8,8,8,0.07)" vertical={false} />
        <XAxis dataKey="bin" tick={{ fill: '#5a5a5a', fontSize: 10 }}
          label={{ value: 'P(active)', position: 'insideBottom', offset: -10, fill: '#5a5a5a', fontSize: 11 }} />
        <YAxis tick={{ fill: '#5a5a5a', fontSize: 10 }} />
        <Tooltip content={<HistTooltip />} cursor={{ fill: 'rgba(8,8,8,0.04)' }} />
        <Legend iconType="square" iconSize={8}
          formatter={(v) => <span style={{ color: '#5a5a5a', fontSize: 11 }}>{v}</span>} />
        <ReferenceLine x="0.50" stroke="oklch(70% 0.13 60)" strokeDasharray="4 3" strokeWidth={1.5} />
        <Bar dataKey="Active"   fill="oklch(66% 0.115 155)" fillOpacity={0.72} radius={[2, 2, 0, 0]} />
        <Bar dataKey="Inactive" fill="oklch(70% 0.16 25)" fillOpacity={0.56} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Molecule card ─────────────────────────────────────────────────────────────

function MolCard({ mol }: { mol: VisualizerMolecule }) {
  const isActive = mol.label === 1
  const isInactive = mol.label === 0
  const borderColor = isActive
    ? 'border-b-green-500'
    : isInactive
      ? 'border-b-red-500'
      : 'border-b-slate-600'

  return (
    <div className={`liquid-panel flex flex-col overflow-hidden border-b-2 ${borderColor}`}>
      <img
        src={moleculeImageUrl(mol.smiles, 240, 150)}
        alt=""
        className="w-full object-contain bg-white"
        style={{ height: 110 }}
        loading="lazy"
        decoding="async"
      />
      <div className="flex flex-col gap-2 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] text-text-tertiary font-mono">#{mol.index}</span>
          {isActive && (
            <span className="rounded-full border border-[rgb(0_215_34_/_0.28)] bg-[rgb(0_215_34_/_0.12)] px-3 py-1.5 text-[10px] font-medium text-[var(--accent-green)]">
              Active
            </span>
          )}
          {isInactive && (
            <span className="rounded-full border border-[rgb(238_29_54_/_0.24)] bg-[rgb(238_29_54_/_0.08)] px-3 py-1.5 text-[10px] font-medium text-[var(--accent-red)]">
              Inactive
            </span>
          )}
          <span className="text-[10px] text-text-secondary font-mono ml-auto">
            P={mol.probability.toFixed(3)}
          </span>
        </div>
        <div className="text-[10.5px] text-text-tertiary font-mono truncate" title={mol.smiles}>
          {mol.smiles}
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

type FilterClass = 'all' | 'active' | 'inactive'
type SortOrder = 'default' | 'prob_asc' | 'prob_desc'

export function VisualizerPage() {
  const { modelLoaded, trainingData } = useAppStore()
  const canUse = modelLoaded && trainingData

  const [page, setPage] = useState(1)
  const [filterClass, setFilterClass] = useState<FilterClass>('all')
  const [sort, setSort] = useState<SortOrder>('default')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1)
    }, 400)
    return () => clearTimeout(t)
  }, [search])

  const q = useQuery({
    queryKey: ['visualizer', page, filterClass, sort, debouncedSearch],
    queryFn: () => getVisualizerData(page, 48, filterClass, sort, debouncedSearch),
    enabled: canUse,
    placeholderData: (prev) => prev,
  })

  const d = q.data

  const handleFilter = (f: FilterClass) => { setFilterClass(f); setPage(1) }
  const handleSort = (s: SortOrder) => { setSort(s); setPage(1) }

  const pageStart = d ? (d.page - 1) * 48 + 1 : 0
  const pageEnd = d ? Math.min(d.page * 48, d.total) : 0

  return (
    <div className="flex flex-col h-full">
      <div className="page-header">
        <h1 className="t-page">Molecule Visualizer</h1>
        <p className="t-caption mt-0.5">Browse training set predictions with ECFP fingerprint distributions</p>
      </div>

      <div className="page-content max-w-6xl space-y-5">
      {!canUse && (
        <div className="status-notice status-notice-warning">
          <AlertCircle size={16} className="shrink-0" /> Load a model and training data in Settings first.
        </div>
      )}

      {canUse && q.isLoading && !d && (
        <div className="liquid-panel px-6 py-16 text-center text-text-tertiary">Computing predictions…</div>
      )}

      {q.isError && (
        <div className="status-notice status-notice-error">{String(q.error)}</div>
      )}

      {d && (
        <>
          {/* Stats row */}
          <div className="grid grid-cols-3 gap-4">
            <StatCard value={d.n_active.toLocaleString()} label="Active molecules" color="text-[var(--accent-green)]" glow="rgba(0,215,34,0.10)" />
            <StatCard value={d.n_inactive.toLocaleString()} label="Inactive molecules" color="text-[var(--accent-red)]" glow="rgba(238,29,54,0.08)" />
            <StatCard value={`${(d.accuracy * 100).toFixed(1)}%`} label="Training accuracy" color="text-[var(--accent-orange)]" glow="rgba(255,107,0,0.10)" />
          </div>

          {/* Histogram */}
          <Card>
            <CardHeader>
              <p className="t-subheading">Prediction Distribution</p>
            </CardHeader>
            <CardBody>
              <Histogram bins={d.hist_bins} active={d.hist_active} inactive={d.hist_inactive} />
            </CardBody>
          </Card>

          {/* Filters */}
          <div className="flex items-center gap-3 flex-wrap">
            <input
              type="text"
              placeholder="Filter by SMILES…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="liquid-control w-64 rounded-md px-5 py-3 text-sm text-text-primary outline-none focus:border-text-primary"
            />
            <div className="liquid-control flex overflow-hidden p-1 text-xs font-medium">
              {(['all', 'active', 'inactive'] as const).map(f => (
                <button key={f}
                  onClick={() => handleFilter(f)}
                  className={`px-5 py-3 text-xs transition-colors ${filterClass === f
                    ? 'rounded-full bg-[var(--accent-blue-deep)] text-white shadow-sm'
                    : 'rounded-full text-text-tertiary hover:bg-white/70 hover:text-text-primary'}`}>
                  {f === 'all' ? 'All' : f === 'active' ? 'Active' : 'Inactive'}
                </button>
              ))}
            </div>
            <select
              value={sort}
              onChange={e => handleSort(e.target.value as SortOrder)}
              className="liquid-control rounded-md px-5 py-3 text-sm text-text-primary outline-none focus:border-text-primary"
            >
              <option value="default">Default order</option>
              <option value="prob_desc">P(active) ↓</option>
              <option value="prob_asc">P(active) ↑</option>
            </select>
            <span className="text-xs text-text-tertiary ml-auto">
              {d.total === 0
                ? 'No molecules'
                : `${pageStart}–${pageEnd} of ${d.total.toLocaleString()}`}
            </span>
          </div>

          {/* Grid */}
          {q.isFetching && (
            <div className="text-center text-text-tertiary text-sm py-2">Loading…</div>
          )}
          {!q.isFetching && d.total === 0 && (
            <div className="liquid-panel px-6 py-10 text-center text-sm text-text-tertiary">No molecules match the current filters.</div>
          )}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {d.molecules.map(mol => (
              <MolCard key={mol.index} mol={mol} />
            ))}
          </div>

          {/* Pagination */}
          {d.n_pages > 1 && (
            <div className="pt-2">
              <Pagination
                page={page}
                totalPages={d.n_pages}
                onPageChange={setPage}
              />
            </div>
          )}
        </>
      )}
      </div>
    </div>
  )
}

function StatCard({ value, label, color, glow }: {
  value: string; label: string; color: string; glow: string
}) {
  return (
    <div className="metric-tile flex flex-col gap-2"
      style={{ boxShadow: `0 18px 42px ${glow}, 0 12px 26px rgb(8 8 8 / 0.08)` }}>
      <p className={`font-mono text-2xl font-semibold tabular-nums ${color}`}>{value}</p>
      <p className="t-label">{label}</p>
    </div>
  )
}
