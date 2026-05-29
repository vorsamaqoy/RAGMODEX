import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getEvaluation } from '../lib/api'
import { useAppStore } from '../store'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { AlertCircle } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts'

// ── helpers ───────────────────────────────────────────────────────────────────

function ds<T>(arr: T[], max = 250): T[] {
  if (arr.length <= max) return arr
  const step = arr.length / max
  return Array.from({ length: max }, (_, i) => arr[Math.round(i * step)])
}

// ── Shared chart tooltip ──────────────────────────────────────────────────────

function CurveTooltip({ active, payload, xLabel, yLabel }: {
  active?: boolean
  payload?: Array<{ payload: { x: number; y: number } }>
  xLabel: string
  yLabel: string
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="glass space-y-1 rounded-md px-4 py-3 text-xs font-mono">
      <div><span className="text-text-tertiary">{xLabel} </span><span className="text-text-primary">{d.x.toFixed(3)}</span></div>
      <div><span className="text-text-tertiary">{yLabel} </span><span className="text-text-primary">{d.y.toFixed(3)}</span></div>
    </div>
  )
}

const axisStyle = { fill: '#5a5a5a', fontSize: 10 } as const
const gridStyle = { stroke: 'rgba(8,8,8,0.08)', strokeDasharray: '2 4' } as const

// ── ROC curve (interactive) ───────────────────────────────────────────────────

function RocChart({ fpr, tpr, auc }: { fpr: number[]; tpr: number[]; auc: number }) {
  const data = ds(fpr.map((x, i) => ({ x, y: tpr[i] })))
  return (
      <div className="space-y-1">
      <p className="text-right font-mono text-xs text-[var(--accent-orange)]">AUC = {auc.toFixed(3)}</p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -12, bottom: 24 }}>
          <CartesianGrid {...gridStyle} />
          <XAxis dataKey="x" type="number" domain={[0, 1]} tickCount={5} tick={axisStyle}
            tickFormatter={v => v.toFixed(2)}
            label={{ value: 'FPR', position: 'insideBottom', offset: -10, fill: '#5a5a5a', fontSize: 11 }} />
          <YAxis type="number" domain={[0, 1]} tickCount={5} tick={axisStyle}
            tickFormatter={v => v.toFixed(2)}
            label={{ value: 'TPR', angle: -90, position: 'insideLeft', offset: 16, fill: '#5a5a5a', fontSize: 11 }} />
          <Tooltip content={(p) => <CurveTooltip {...p as Parameters<typeof CurveTooltip>[0]} xLabel="FPR" yLabel="TPR" />} />
          <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
            stroke="rgba(8,8,8,0.18)" strokeDasharray="4 4" strokeWidth={1} />
          <Line dataKey="y" stroke="oklch(70% 0.13 60)" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Precision-Recall curve (interactive) ─────────────────────────────────────

function PrChart({ recall, precision, ap }: { recall: number[]; precision: number[]; ap: number }) {
  const data = ds(recall.map((x, i) => ({ x, y: precision[i] })))
  return (
    <div className="space-y-1">
      <p className="text-right font-mono text-xs text-[var(--accent-green)]">AP = {ap.toFixed(3)}</p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -12, bottom: 24 }}>
          <CartesianGrid {...gridStyle} />
          <XAxis dataKey="x" type="number" domain={[0, 1]} tickCount={5} tick={axisStyle}
            tickFormatter={v => v.toFixed(2)}
            label={{ value: 'Recall', position: 'insideBottom', offset: -10, fill: '#5a5a5a', fontSize: 11 }} />
          <YAxis type="number" domain={[0, 1]} tickCount={5} tick={axisStyle}
            tickFormatter={v => v.toFixed(2)}
            label={{ value: 'Precision', angle: -90, position: 'insideLeft', offset: 20, fill: '#5a5a5a', fontSize: 11 }} />
          <Tooltip content={(p) => <CurveTooltip {...p as Parameters<typeof CurveTooltip>[0]} xLabel="Recall" yLabel="Prec" />} />
          <Line dataKey="y" stroke="oklch(66% 0.115 155)" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Confusion matrix ──────────────────────────────────────────────────────────

function ConfusionMatrix({ cm }: { cm: number[][] }) {
  const labels = ['Inactive', 'Active']
  const flat = cm.flat()
  const max = Math.max(...flat)
  return (
    <figure role="img" aria-label="Confusion matrix showing predicted vs actual classifications">
      <div className="space-y-2">
        <p className="mb-3 text-xs text-text-tertiary">Predicted {">"}</p>
        <div className="grid grid-cols-3 gap-1 text-xs text-center">
          <div />
          {labels.map(l => <div key={l} className="pb-1 text-text-tertiary">{l}</div>)}
          {cm.map((row, ri) => [
            <div key={`l${ri}`} className="flex items-center justify-end pr-2 text-text-tertiary">{labels[ri]}</div>,
            ...row.map((v, ci) => (
              <div key={`${ri}${ci}`}
                className="flex aspect-square items-center justify-center rounded-md font-mono text-sm font-semibold text-text-primary"
                style={{ background: `rgb(0 215 34 / ${(v / max) * 0.34 + 0.08})` }}>
                {v}
              </div>
            )),
          ])}
        </div>
        <p className="mt-2 text-xs text-text-tertiary">Actual</p>
      </div>
    </figure>
  )
}

// ── KPI card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="metric-tile text-center">
      <p className={`font-mono text-2xl font-semibold tabular-nums ${color}`}>{value}</p>
      <p className="t-label mt-2">{label}</p>
    </div>
  )
}

// ── Tab button ────────────────────────────────────────────────────────────────

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`min-h-11 rounded-sm px-5 py-2.5 text-sm font-semibold transition-all ${
        active
          ? 'btn-glow text-white'
          : 'text-text-tertiary hover:bg-bg-elevated hover:text-text-primary'
      }`}
    >
      {children}
    </button>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function EvaluatePage() {
  const { modelLoaded, trainingData } = useAppStore()
  const canEval = modelLoaded && trainingData
  const [tab, setTab] = useState<'train' | 'test'>('train')

  const q = useQuery({
    queryKey: ['evaluate'],
    queryFn: getEvaluation,
    enabled: canEval,
  })

  const d = q.data

  return (
    <div className="flex flex-col h-full">
      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="t-page">Model Evaluation</h1>
          <p className="t-caption mt-0.5">Cross-validation metrics, ROC curve, confusion matrix</p>
        </div>
        {canEval && (
          <Button variant="secondary" size="sm" onClick={() => q.refetch()} loading={q.isFetching}>
            Refresh
          </Button>
        )}
      </div>

      <div className="page-content max-w-5xl space-y-6">
      {!canEval && (
        <div className="status-notice status-notice-warning">
          <AlertCircle size={16} className="shrink-0" /> Load a model and training data in Settings first.
        </div>
      )}

      {canEval && q.isLoading && (
        <div className="liquid-panel px-6 py-12 text-center text-text-tertiary">Computing metrics…</div>
      )}

      {q.isError && (
        <div className="status-notice status-notice-error">{String(q.error)}</div>
      )}

      {d && (
        <>
          {/* Tab switcher */}
          <div className="flex gap-2 border-b border-border-subtle pb-3">
            <TabButton active={tab === 'train'} onClick={() => setTab('train')}>Training Set</TabButton>
            <TabButton active={tab === 'test'} onClick={() => setTab('test')}>Test Set</TabButton>
          </div>

          {/* Training Set tab */}
          {tab === 'train' && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard label="ROC-AUC" value={d.roc_auc.toFixed(4)} color="text-[var(--accent-orange)]" />
                <KpiCard label="PR-AUC"  value={d.pr_auc.toFixed(4)}  color="text-[var(--accent-orange)]" />
                <KpiCard label="Active"   value={String(d.n_active)}   color="text-[var(--accent-green)]" />
                <KpiCard label="Inactive" value={String(d.n_inactive)} color="text-[var(--accent-red)]" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader><p className="t-subheading">ROC Curve</p></CardHeader>
                  <CardBody>
                    <RocChart fpr={d.roc_curve.fpr} tpr={d.roc_curve.tpr} auc={d.roc_auc} />
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader><p className="t-subheading">Precision-Recall Curve</p></CardHeader>
                  <CardBody>
                    <PrChart recall={d.pr_curve.recall} precision={d.pr_curve.precision} ap={d.pr_auc} />
                  </CardBody>
                </Card>

                <Card>
                  <CardHeader><p className="t-subheading">Confusion Matrix</p></CardHeader>
                  <CardBody>
                    <ConfusionMatrix cm={d.confusion_matrix} />
                  </CardBody>
                </Card>
              </div>
            </>
          )}

          {/* Test Set tab */}
          {tab === 'test' && (
            <>
              {!d.test_roc_auc ? (
                <div className="status-notice status-notice-warning">
                  <AlertCircle size={15} /> Upload a test CSV in Settings &rarr; Upload Test Data first.
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <KpiCard label="ROC-AUC" value={d.test_roc_auc.toFixed(4)} color="text-[var(--accent-orange)]" />
                    <KpiCard label="PR-AUC"  value={d.test_pr_auc!.toFixed(4)}  color="text-[var(--accent-orange)]" />
                    <KpiCard label="Active"   value={String(d.test_n_active)}   color="text-[var(--accent-green)]" />
                    <KpiCard label="Inactive" value={String(d.test_n_inactive)} color="text-[var(--accent-red)]" />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Card>
                      <CardHeader><p className="t-subheading">ROC Curve</p></CardHeader>
                      <CardBody>
                        <RocChart fpr={d.test_roc_curve!.fpr} tpr={d.test_roc_curve!.tpr} auc={d.test_roc_auc} />
                      </CardBody>
                    </Card>

                    <Card>
                      <CardHeader><p className="t-subheading">Precision-Recall Curve</p></CardHeader>
                      <CardBody>
                        <PrChart recall={d.test_pr_curve!.recall} precision={d.test_pr_curve!.precision} ap={d.test_pr_auc!} />
                      </CardBody>
                    </Card>

                    <Card>
                      <CardHeader><p className="t-subheading">Confusion Matrix</p></CardHeader>
                      <CardBody>
                        <ConfusionMatrix cm={d.test_confusion_matrix!} />
                      </CardBody>
                    </Card>
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}
      </div>
    </div>
  )
}
