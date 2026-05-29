import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { runScreening } from '../lib/api'
import { useAppStore } from '../store'
import { Card, CardBody } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Download,
  Upload,
} from 'lucide-react'

export function ScreeningPage() {
  const modelLoaded = useAppStore(s => s.modelLoaded)
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)

  const mut = useMutation({ mutationFn: () => runScreening(file!) })

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }, [])

  const results = mut.data?.results ?? []
  const active = results.filter(r => r.prediction === 'Active').length
  const inactive = results.filter(r => r.prediction === 'Inactive').length

  function downloadCsv() {
    const header = 'smiles,probability,prediction\n'
    const rows = results.map(r => `${r.smiles},${r.probability ?? ''},${r.prediction ?? ''}`).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'screening_results.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="page-header">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="t-page">Virtual Screening</h1>
            <p className="t-caption mt-1">Batch SMILES prediction from CSV, TXT, or SMI files</p>
          </div>
        </div>
      </div>

      <div className="page-content max-w-7xl space-y-6">
      {!modelLoaded && (
        <div role="alert" className="page-enter status-notice status-notice-warning">
          <AlertCircle size={17} className="shrink-0" /> No model loaded. Go to Settings before running a batch.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        <section className="page-enter liquid-panel p-8 md:p-10">
          <div className="mb-7 flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-2xl">
              <p className="t-label" style={{ color: 'var(--accent-purple)' }}>Batch intake</p>
              <h2 className="mt-2 text-2xl font-bold text-text-primary md:text-3xl">Screen a molecular library</h2>
              <p className="mt-2 max-w-xl text-sm leading-6 text-text-secondary">
                Upload a SMILES list and run the current model across the full set.
              </p>
            </div>
            <div className="rounded-md border border-white/70 bg-white/60 px-5 py-4 text-right shadow-[inset_0_1px_0_rgb(255_255_255_/_0.72)]">
              <p className="t-label">Queue</p>
              <p className="mt-1 text-2xl font-bold tabular-nums text-brand">{file ? '01' : '00'}</p>
            </div>
          </div>

          <div
            role="button"
            tabIndex={0}
            aria-label="Click or drop a CSV or TXT file here to upload"
            onDrop={onDrop}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            className={`group interactive-surface relative min-h-[280px] cursor-pointer overflow-hidden rounded-md border border-dashed p-8 text-center transition-all duration-300 md:min-h-[340px] md:p-12 ${
              dragging
                ? 'border-[var(--accent-blue-deep)] bg-white/80 shadow-[0_18px_42px_rgb(0_106_204_/_0.14)]'
                : 'border-[rgb(8_8_8_/_0.18)] bg-white/58 hover:border-[var(--glass-border-strong)] hover:bg-white/76'
            }`}
            onClick={() => document.getElementById('screen-file-input')?.click()}
            onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); document.getElementById('screen-file-input')?.click() } }}
          >
            <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-black/30 to-transparent" />
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full border text-white shadow-[0_16px_34px_rgb(0_106_204_/_0.20)] transition-transform duration-300 group-hover:scale-105"
              style={{ background: 'var(--accent-blue-info)', borderColor: 'var(--accent-blue-info)' }}>
              {file ? <CheckCircle2 size={34} /> : <Upload size={34} />}
            </div>
            <p className="mt-6 text-xl font-bold text-text-primary md:text-2xl">
              {file ? file.name : 'Drop your screening file'}
            </p>
            <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-text-secondary">
              CSV with a smiles column, TXT, or SMI. The file is staged locally before the model run.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-2">
              <span className="rounded-full border border-white/70 bg-white/68 px-4 py-2 text-xs font-medium text-text-secondary shadow-sm">.csv</span>
              <span className="rounded-full border border-white/70 bg-white/68 px-4 py-2 text-xs font-medium text-text-secondary shadow-sm">.txt</span>
              <span className="rounded-full border border-white/70 bg-white/68 px-4 py-2 text-xs font-medium text-text-secondary shadow-sm">.smi</span>
            </div>
            <input id="screen-file-input" type="file" accept=".csv,.txt,.smi" className="hidden"
              aria-label="Upload SMILES file (CSV, TXT, or SMI format)"
              onChange={e => setFile(e.target.files?.[0] ?? null)} />
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Button disabled={!file || !modelLoaded} loading={mut.isPending} onClick={() => mut.mutate()} size="lg">
              <Activity size={17} />
              Run Screening
            </Button>
            {file && (
              <Button variant="secondary" onClick={() => setFile(null)}>
                Clear file
              </Button>
            )}
          </div>
        </section>

      </div>

      {mut.error && <div className="status-notice status-notice-error">{String(mut.error)}</div>}

      {mut.data && (
        <div className="page-enter stagger-2 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-white/70 bg-white/68 px-4 py-2 text-sm font-medium text-text-secondary shadow-sm">
              {mut.data.n_total} molecules screened
            </span>
            <Badge variant="active">{active} Active</Badge>
            <Badge variant="inactive">{inactive} Inactive</Badge>
            <Button variant="secondary" size="sm" onClick={downloadCsv} className="ml-auto">
              <Download size={14} /> Export CSV
            </Button>
          </div>

          <Card>
            <CardBody className="overflow-x-auto pt-5">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border-default text-text-tertiary text-left">
                    <th className="pb-2 pr-4">#</th>
                    <th className="pb-2 pr-4">SMILES</th>
                    <th className="pb-2 pr-4">P(active)</th>
                    <th className="pb-2">Prediction</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i} className="border-b border-border-subtle hover:bg-white/55">
                      <td className="py-3 pr-4 text-text-tertiary">{i + 1}</td>
                      <td className="py-3 pr-4 font-mono text-text-secondary max-w-xs truncate">{r.smiles}</td>
                      <td className="py-3 pr-4 font-mono text-text-secondary">
                        {r.probability != null ? (r.probability * 100).toFixed(1) + '%' : '—'}
                      </td>
                      <td className="py-2">
                        {r.prediction ? (
                          <Badge variant={r.prediction === 'Active' ? 'active' : r.prediction === 'Inactive' ? 'inactive' : 'neutral'}>
                            {r.prediction}
                          </Badge>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>
        </div>
      )}
      </div>
    </div>
  )
}
