import { useEffect, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { uploadModel, uploadTrainingData, uploadTestData, setLlmConfig, getModelStatus, getLlmCatalog } from '../lib/api'
import { useAppStore } from '../store'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/shadcn/select'
import { Tooltip, TooltipContent, TooltipTrigger } from '../components/shadcn/tooltip'
import { Checkbox } from '../components/shadcn/checkbox'
import { CheckCircle, Cpu, Database, FileCheck2, HelpCircle, KeyRound, Lock, RefreshCw, Server, SlidersHorizontal, Upload, XCircle } from 'lucide-react'
import { cn } from '../lib/cn'

const PROVIDERS: Record<string, string[]> = {
  groq: ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'qwen/qwen3-32b'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'],
  anthropic: ['claude-opus-4-7', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001'],
}

const triggerCls =
  'min-h-12 w-full rounded-md border border-white/70 bg-white/[0.72] px-4 text-sm font-medium text-text-primary ' +
  'shadow-[0_12px_28px_rgb(8_8_8_/_0.07),inset_0_1px_0_rgb(255_255_255_/_0.82)] backdrop-blur-md ' +
  'transition-all hover:border-[rgb(0_106_204_/_0.30)] focus:border-[var(--accent-blue-deep)] focus:ring-2 focus:ring-[var(--accent-blue-deep)]/15'

type StatusIcon = typeof Cpu

function FileDropZone({
  file,
  accept,
  hint,
  onChange,
  inputAriaLabel,
}: {
  file: File | null
  accept: string
  hint: string
  onChange: (f: File | null) => void
  inputAriaLabel?: string
}) {
  return (
    <label className="block cursor-pointer group">
      <div className={cn(
        'flex min-h-14 items-center gap-3 rounded-md px-4 py-3 transition-all duration-200',
        'border border-white/70 bg-white/70 shadow-[0_12px_26px_rgb(8_8_8_/_0.06),inset_0_1px_0_rgb(255_255_255_/_0.80)] backdrop-blur-md',
        'hover:-translate-y-0.5 hover:border-[rgb(0_106_204_/_0.28)] hover:bg-white/[0.82] hover:shadow-[0_16px_32px_rgb(8_8_8_/_0.08)]',
        file && 'border-[rgb(0_215_34_/_0.36)] bg-[rgb(0_215_34_/_0.08)]',
      )}>
        <span className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-full',
          file ? 'bg-[rgb(0_215_34_/_0.16)] text-[var(--accent-green)]' : 'bg-[rgb(8_8_8_/_0.055)] text-text-tertiary group-hover:text-[var(--accent-blue-deep)]',
        )}>
          <Upload size={16} />
        </span>
        <span className={cn('flex-1 truncate text-sm font-medium', file ? 'text-text-primary' : 'text-text-tertiary')}>
          {file ? file.name : hint}
        </span>
        {file && (
          <button
            type="button"
            onClick={e => { e.preventDefault(); onChange(null) }}
            className="-m-2 rounded p-2 text-text-tertiary transition-colors hover:text-[var(--accent-red)]"
          >
            <XCircle size={14} />
          </button>
        )}
      </div>
      <input
        type="file"
        accept={accept}
        className="hidden"
        aria-label={inputAriaLabel ?? hint}
        onChange={e => onChange(e.target.files?.[0] ?? null)}
      />
    </label>
  )
}

export function SettingsPage() {
  const { setModelStatus, setLlmStatus } = useAppStore()
  const [modelFile, setModelFile] = useState<File | null>(null)
  const [trainingFile, setTrainingFile] = useState<File | null>(null)
  const [testFile, setTestFile] = useState<File | null>(null)
  const [provider, setProvider] = useState('groq')
  const [model, setModel] = useState(PROVIDERS.groq[0])
  const [temperature, setTemperature] = useState(0.3)
  const [apiKey, setApiKey] = useState('')
  const [persistApiKey, setPersistApiKey] = useState(false)
  const [lockedKeys, setLockedKeys] = useState<Record<string, boolean>>(() => {
    try { return JSON.parse(localStorage.getItem('ragmodex_locked_llm_keys') ?? '{}') } catch { return {} }
  })
  const [localEndpoint, setLocalEndpoint] = useState('http://127.0.0.1:11434')
  const [fpRadius, setFpRadius] = useState(3)
  const [fpNbits, setFpNbits] = useState(2048)

  const statusQ = useQuery({ queryKey: ['model-status'], queryFn: getModelStatus })
  const catalogQ = useQuery({ queryKey: ['llm-catalog'], queryFn: getLlmCatalog })

  useEffect(() => {
    if (!statusQ.data) return
    if (typeof statusQ.data.fp_radius === 'number') setFpRadius(statusQ.data.fp_radius)
    if (typeof statusQ.data.fp_nbits === 'number') setFpNbits(statusQ.data.fp_nbits)
    if (statusQ.data.llm_provider) setProvider(statusQ.data.llm_provider)
    if (statusQ.data.llm_model) setModel(statusQ.data.llm_model)
    if (typeof statusQ.data.temperature === 'number') setTemperature(statusQ.data.temperature)
  }, [statusQ.data])

  useEffect(() => {
    if (!catalogQ.data) return
    setProvider(catalogQ.data.provider)
    setModel(catalogQ.data.model)
    setTemperature(catalogQ.data.temperature)
    setLocalEndpoint(catalogQ.data.local_endpoint)
  }, [catalogQ.data])

  useEffect(() => {
    try { localStorage.setItem('ragmodex_locked_llm_keys', JSON.stringify(lockedKeys)) } catch {}
  }, [lockedKeys])

  const uploadModelMut = useMutation({
    mutationFn: () => uploadModel(modelFile!),
    onSuccess: async () => {
      const res = await statusQ.refetch()
      if (res.data) setModelStatus({
        modelLoaded: !!res.data.model_loaded,
        trainingData: !!res.data.training_data,
        modelName: String(res.data.model_name ?? ''),
        nMolecules: res.data.n_molecules,
      })
      toast.success('Model loaded successfully')
    },
    onError: (err) => toast.error(String(err)),
  })

  const uploadDataMut = useMutation({
    mutationFn: () => uploadTrainingData(trainingFile!, 'smiles', 'label', fpRadius, fpNbits),
    onSuccess: d => {
      setModelStatus({ modelLoaded: true, trainingData: true, modelName: '', nMolecules: d.n_molecules })
      statusQ.refetch()
      toast.success(`${d.n_molecules} molecules loaded (${d.active} active / ${d.inactive} inactive)`)
    },
    onError: (err) => toast.error(String(err)),
  })

  const uploadTestMut = useMutation({
    mutationFn: () => uploadTestData(testFile!, 'smiles', 'label', fpRadius, fpNbits),
    onSuccess: (d) => {
      statusQ.refetch()
      toast.success(`Test set loaded - ${d.n_molecules} molecules`)
    },
    onError: (err) => toast.error(String(err)),
  })

  const llmMut = useMutation({
    mutationFn: () => setLlmConfig(provider, model, temperature, {
      apiKey: lockedKeys[provider] ? undefined : apiKey,
      persistApiKey,
      localEndpoint,
    }),
    onSuccess: d => {
      setLlmStatus({ provider: d.provider, model: d.model, temperature })
      if (apiKey && persistApiKey) setLockedKeys(current => ({ ...current, [provider]: true }))
      setApiKey('')
      catalogQ.refetch()
      toast.success('LLM configuration saved')
    },
    onError: (err) => toast.error(String(err)),
  })

  const s = statusQ.data
  const providers = catalogQ.data?.providers ?? Object.entries(PROVIDERS).map(([name, models]) => ({
    name,
    available: true,
    requires_key: name !== 'local',
    key_configured: false,
    default_model: models[0],
    models,
  }))
  const selectedProvider = providers.find(p => p.name === provider) ?? providers[0]
  const providerModels = selectedProvider?.models?.length ? selectedProvider.models : (PROVIDERS[provider] ?? [model])
  const keyLocked = !!lockedKeys[provider]

  return (
    <div className="flex h-full flex-col">
      <div className="page-header">
        <div>
          <h1 className="t-page">Settings</h1>
          <p className="t-caption mt-0.5">Upload model, datasets, and configure the LLM</p>
        </div>
      </div>

      <div
        className="page-content flex-1"
        style={{
          background:
            'linear-gradient(135deg, rgb(122 61 255 / 0.055), rgb(59 137 255 / 0.045) 36%, rgb(0 215 34 / 0.035) 100%)',
        }}
      >
        <div className="mx-auto max-w-6xl space-y-7">
          {s && (
            <div className="grid gap-4 md:grid-cols-4">
              <StatusItem ok={s.model_loaded} icon={Cpu} label="Model" detail={s.model_name || 'Not loaded'} />
              <StatusItem ok={s.training_data} icon={Database} label="Training data" detail={s.n_molecules > 0 ? `${s.n_molecules} molecules` : 'Not loaded'} />
              <StatusItem ok={!!s.test_data} icon={FileCheck2} label="Test data" detail={s.n_test > 0 ? `${s.n_test} molecules` : 'Optional'} />
              <StatusItem ok icon={SlidersHorizontal} label="Fingerprint" detail={`r${s.fp_radius ?? fpRadius} / ${s.fp_nbits ?? fpNbits} bits`} />
            </div>
          )}

          <div className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
            <section className="space-y-5">
              <div className="space-y-1">
                <p className="t-label text-[var(--accent-blue-deep)]">Assets</p>
                <h2 className="t-subheading">Model and datasets</h2>
              </div>

              <Card className="border border-white/70 bg-white/[0.66] shadow-[0_20px_52px_rgb(8_8_8_/_0.09)] backdrop-blur-xl">
                <CardHeader className="flex items-start gap-4">
                  <div className="flex size-11 shrink-0 items-center justify-center rounded-md bg-[rgb(122_61_255_/_0.10)] text-[var(--accent-purple)]">
                    <Cpu size={20} />
                  </div>
                  <div>
                    <p className="t-subheading">Upload model</p>
                    <p className="t-caption mt-1">Scikit-learn classifier saved with pickle or joblib (.pkl / .joblib)</p>
                  </div>
                </CardHeader>
                <CardBody className="space-y-4">
                  <FileDropZone file={modelFile} accept=".pkl,.joblib" hint="Choose .pkl or .joblib file..." onChange={setModelFile} inputAriaLabel="Upload scikit-learn model (.pkl or .joblib)" />
                  <Button disabled={!modelFile} loading={uploadModelMut.isPending} onClick={() => uploadModelMut.mutate()} size="md">
                    <Upload size={16} /> Upload model
                  </Button>
                </CardBody>
              </Card>

              <Card className="border border-white/70 bg-white/[0.64] shadow-[0_18px_44px_rgb(8_8_8_/_0.08)] backdrop-blur-xl">
                <CardHeader className="flex items-start gap-4">
                  <div className="flex size-11 shrink-0 items-center justify-center rounded-md bg-[rgb(0_215_34_/_0.10)] text-[var(--accent-green)]">
                    <SlidersHorizontal size={20} />
                  </div>
                  <div>
                    <p className="t-subheading">Fingerprint parameters</p>
                    <p className="t-caption mt-1">Used when building training and test fingerprints.</p>
                  </div>
                </CardHeader>
                <CardBody className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="t-label block">Morgan radius</span>
                    <input
                      type="number"
                      min={0}
                      max={6}
                      step={1}
                      value={fpRadius}
                      onChange={e => setFpRadius(Math.max(0, Number(e.target.value) || 0))}
                      className="input-glass liquid-control w-full rounded-md px-5 py-3 text-base leading-[1.35] text-text-primary"
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="t-label block">Vector length</span>
                    <input
                      type="number"
                      min={128}
                      step={128}
                      value={fpNbits}
                      onChange={e => setFpNbits(Math.max(128, Number(e.target.value) || 2048))}
                      className="input-glass liquid-control w-full rounded-md px-5 py-3 text-base leading-[1.35] text-text-primary"
                    />
                  </label>
                  <p className="t-caption md:col-span-2">
                    Defaults are radius 3 and 2048 bits. Keep these values aligned with the uploaded model feature count.
                  </p>
                </CardBody>
              </Card>

              <div className="grid gap-5 lg:grid-cols-2">
                <Card className="border border-white/70 bg-white/[0.64] shadow-[0_18px_44px_rgb(8_8_8_/_0.08)] backdrop-blur-xl">
                  <CardHeader className="flex items-start gap-4">
                    <div className="flex size-11 shrink-0 items-center justify-center rounded-md bg-[rgb(59_137_255_/_0.10)] text-[var(--accent-blue-deep)]">
                      <Database size={20} />
                    </div>
                    <div>
                      <p className="t-subheading">Training data</p>
                      <p className="t-caption mt-1">CSV with columns "smiles" and "label" (0 / 1)</p>
                    </div>
                  </CardHeader>
                  <CardBody className="space-y-4">
                    <FileDropZone file={trainingFile} accept=".csv" hint="Choose CSV file..." onChange={setTrainingFile} inputAriaLabel="Upload training CSV file" />
                    <Button disabled={!trainingFile} loading={uploadDataMut.isPending} onClick={() => uploadDataMut.mutate()} size="md">
                      <Upload size={16} /> Upload dataset
                    </Button>
                  </CardBody>
                </Card>

                <Card className="border border-white/70 bg-white/[0.64] shadow-[0_18px_44px_rgb(8_8_8_/_0.08)] backdrop-blur-xl">
                  <CardHeader className="flex items-start gap-4">
                    <div className="flex size-11 shrink-0 items-center justify-center rounded-md bg-[rgb(255_174_19_/_0.14)] text-[var(--accent-yellow)]">
                      <FileCheck2 size={20} />
                    </div>
                    <div>
                      <p className="t-subheading">Test data</p>
                      <p className="t-caption mt-1">Optional CSV for evaluation metrics</p>
                    </div>
                  </CardHeader>
                  <CardBody className="space-y-4">
                    <FileDropZone file={testFile} accept=".csv" hint="Choose CSV file..." onChange={setTestFile} inputAriaLabel="Upload test CSV file" />
                    <Button disabled={!testFile} loading={uploadTestMut.isPending} onClick={() => uploadTestMut.mutate()} size="md">
                      <Upload size={16} /> Upload test set
                    </Button>
                  </CardBody>
                </Card>
              </div>
            </section>

            <section className="space-y-5">
              <div className="space-y-1">
                <p className="t-label text-[var(--accent-green)]">LLM</p>
                <h2 className="t-subheading">Response engine</h2>
              </div>

              <Card className="sticky top-5 border border-white/70 bg-white/[0.68] shadow-[0_22px_56px_rgb(8_8_8_/_0.10)] backdrop-blur-xl">
                <CardHeader className="flex items-start gap-4">
                  <div className="flex size-11 shrink-0 items-center justify-center rounded-md bg-[rgb(0_215_34_/_0.12)] text-[var(--accent-green)]">
                    <SlidersHorizontal size={20} />
                  </div>
                  <div>
                    <p className="t-subheading">LLM configuration</p>
                    <p className="t-caption mt-1">Choose provider, model, and response variability.</p>
                  </div>
                </CardHeader>
                <CardBody className="space-y-5">
                  <div className="space-y-2">
                    <label className="t-label block">Provider</label>
                    <Select value={provider} onValueChange={v => {
                      const nextProvider = providers.find(p => p.name === v)
                      setProvider(v)
                      setModel(nextProvider?.models?.[0] ?? '')
                      setApiKey('')
                    }}>
                      <SelectTrigger className={triggerCls}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {providers.map(p => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.name}{p.requires_key && !p.key_configured ? ' - key needed' : ''}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="t-label block">Model</label>
                    <Select value={model} onValueChange={setModel}>
                      <SelectTrigger className={triggerCls}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {providerModels.map(m => (
                          <SelectItem key={m} value={m}>{m}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {provider === 'local' && (
                    <div className="rounded-md border border-white/70 bg-white/[0.58] p-4 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.78)]">
                      <div className="mb-3 flex items-center gap-2">
                        <Server size={15} className="text-[var(--accent-blue-deep)]" />
                        <label className="t-label">Local endpoint</label>
                        <button
                          type="button"
                          onClick={() => catalogQ.refetch()}
                          className="ml-auto rounded p-1 text-text-tertiary transition-colors hover:text-[var(--accent-blue-deep)]"
                          aria-label="Refresh local model list"
                          title="Refresh local model list"
                        >
                          <RefreshCw size={14} />
                        </button>
                      </div>
                      <input
                        type="url"
                        value={localEndpoint}
                        onChange={e => setLocalEndpoint(e.target.value)}
                        className="input-glass liquid-control w-full rounded-md px-4 py-3 text-sm text-text-primary"
                        placeholder="http://127.0.0.1:11434"
                      />
                      <p className="t-caption mt-3">
                        Local models are read from Ollama when available. Pull or create a model locally and refresh this list.
                      </p>
                    </div>
                  )}

                  {selectedProvider?.requires_key && (
                    <div className="rounded-md border border-white/70 bg-white/[0.58] p-4 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.78)]">
                      <div className="mb-3 flex items-center gap-2">
                        <KeyRound size={15} className="text-[var(--accent-orange)]" />
                        <label className="t-label">API key</label>
                        {selectedProvider.key_configured && (
                          <span className="ml-auto rounded-full bg-[rgb(0_215_34_/_0.12)] px-2 py-1 text-xs font-semibold text-[var(--accent-green)]">
                            configured
                          </span>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <input
                          type="password"
                          value={keyLocked ? 'locked-key' : apiKey}
                          disabled={keyLocked}
                          onChange={e => setApiKey(e.target.value)}
                          className="input-glass liquid-control min-w-0 flex-1 rounded-md px-4 py-3 text-sm text-text-primary disabled:cursor-not-allowed disabled:opacity-70"
                          placeholder={selectedProvider.key_configured ? 'Leave empty to keep current key' : `${provider.toUpperCase()} API key`}
                        />
                        {keyLocked && (
                          <button
                            type="button"
                            onClick={() => setLockedKeys(current => ({ ...current, [provider]: false }))}
                            className="liquid-control inline-flex items-center gap-2 rounded-md px-3 text-xs font-semibold text-text-primary"
                          >
                            <Lock size={14} /> Unlock
                          </button>
                        )}
                      </div>
                      <label className="mt-4 flex items-start gap-3 text-sm text-text-secondary">
                        <Checkbox
                          checked={persistApiKey}
                          onCheckedChange={v => setPersistApiKey(v === true)}
                          className="mt-0.5"
                          disabled={keyLocked}
                        />
                        <span>
                          Save permanently in the project .env and lock this provider field after saving.
                        </span>
                      </label>
                    </div>
                  )}

                  <div className="rounded-md border border-white/70 bg-white/[0.58] p-4 shadow-[inset_0_1px_0_rgb(255_255_255_/_0.78)]">
                    <div className="mb-3 flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <label className="t-label">Temperature</label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button type="button" tabIndex={-1} className="text-text-tertiary transition-colors hover:text-[var(--accent-blue-deep)]">
                              <HelpCircle size={12} />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-[220px] text-xs leading-relaxed">
                            Controls LLM output randomness. Lower values produce focused, deterministic answers; higher values produce more creative responses.
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <span className="t-mono text-[var(--accent-orange)]">{temperature.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={temperature}
                      onChange={e => setTemperature(Number(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  <Button onClick={() => llmMut.mutate()} loading={llmMut.isPending} size="md" className="w-full">
                    Save configuration
                  </Button>
                </CardBody>
              </Card>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusItem({ ok, icon: Icon, label, detail }: { ok: boolean; icon: StatusIcon; label: string; detail: string }) {
  return (
    <div className={cn(
      'flex items-center gap-4 rounded-md border p-4 shadow-[0_16px_38px_rgb(8_8_8_/_0.07)] backdrop-blur-xl',
      ok ? 'border-[rgb(0_215_34_/_0.32)] bg-[rgb(0_215_34_/_0.08)]' : 'border-white/70 bg-white/[0.64]',
    )}>
      <div className={cn(
        'flex size-11 shrink-0 items-center justify-center rounded-md',
        ok ? 'bg-[rgb(0_215_34_/_0.15)] text-[var(--accent-green)]' : 'bg-[rgb(8_8_8_/_0.055)] text-text-tertiary',
      )}>
        <Icon size={20} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-text-primary">{label}</span>
          {ok
            ? <CheckCircle size={14} className="shrink-0 text-[var(--accent-green)]" />
            : <XCircle size={14} className="shrink-0 text-text-disabled" />
          }
        </div>
        <span className="block truncate text-sm text-text-tertiary">{detail}</span>
      </div>
    </div>
  )
}
