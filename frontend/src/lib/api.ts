const BASE = '/api'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, init)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? res.statusText)
  }
  return res.json()
}

// ── Health ──────────────────────────────────────────────────────────────────
export const getHealth = () => req<Record<string, unknown>>('/health')

// ── Model ───────────────────────────────────────────────────────────────────
export const uploadModel = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return req<{ ok: boolean; model_name: string }>('/model/upload', { method: 'POST', body: fd })
}

export const uploadTrainingData = (file: File, smiles_col = 'smiles', label_col = 'label', radius = 3, nbits = 2048) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('smiles_col', smiles_col)
  fd.append('label_col', label_col)
  fd.append('radius', String(radius))
  fd.append('nbits', String(nbits))
  return req<{ ok: boolean; n_molecules: number; active: number; inactive: number }>('/model/training-data', { method: 'POST', body: fd })
}

export const uploadTestData = (file: File, smiles_col = 'smiles', label_col = 'label', radius = 3, nbits = 2048) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('smiles_col', smiles_col)
  fd.append('label_col', label_col)
  fd.append('radius', String(radius))
  fd.append('nbits', String(nbits))
  return req<{ ok: boolean; n_molecules: number; active: number; inactive: number }>('/model/training-data/test', { method: 'POST', body: fd })
}

export const setLlmConfig = (
  provider: string,
  model: string,
  temperature: number,
  options: { apiKey?: string; persistApiKey?: boolean; localEndpoint?: string } = {},
) => {
  const fd = new FormData()
  fd.append('provider', provider)
  fd.append('model', model)
  fd.append('temperature', String(temperature))
  if (options.apiKey) fd.append('api_key', options.apiKey)
  fd.append('persist_api_key', String(!!options.persistApiKey))
  if (options.localEndpoint) fd.append('local_endpoint', options.localEndpoint)
  return req<{ ok: boolean; provider: string; model: string }>('/model/config', { method: 'POST', body: fd })
}

export const getModelStatus = () => req<{
  model_loaded: boolean; training_data: boolean; model_name: string; n_molecules: number;
  fp_radius: number; fp_nbits: number; test_data: boolean; n_test: number;
  llm_provider: string; llm_model: string; temperature: number
}>('/model/status')

export const getSavedSession = () => req<{
  exists: boolean; model_loaded: boolean; training_data: boolean; test_data: boolean;
  model_name: string; n_molecules: number; n_test: number; fp_radius: number;
  fp_nbits: number; saved_at: string | null
}>('/model/session')

export const saveSession = () => req<{
  exists: boolean; model_loaded: boolean; training_data: boolean; test_data: boolean;
  model_name: string; n_molecules: number; n_test: number; fp_radius: number;
  fp_nbits: number; saved_at: string | null
}>('/model/session/save', { method: 'POST' })

export const restoreSession = () => req<{
  ok: boolean; model_loaded: boolean; training_data: boolean; model_name: string;
  n_molecules: number; fp_radius: number; fp_nbits: number; test_data: boolean;
  n_test: number; llm_provider: string; llm_model: string; temperature: number
}>('/model/session/restore', { method: 'POST' })

export const clearSavedSession = () =>
  req<{ ok: boolean; exists: boolean }>('/model/session/clear', { method: 'POST' })

export const startNewSession = () => req<{
  ok: boolean; model_loaded: boolean; training_data: boolean; model_name: string;
  n_molecules: number; fp_radius: number; fp_nbits: number; test_data: boolean;
  n_test: number; llm_provider: string; llm_model: string; temperature: number
}>('/model/session/new', { method: 'POST' })

export const getLlmCatalog = () => req<LlmCatalog>('/model/llm/catalog')

export const pullLocalModel = (modelName: string, localEndpoint = 'http://127.0.0.1:11434') => {
  const fd = new FormData()
  fd.append('model_name', modelName)
  fd.append('local_endpoint', localEndpoint)
  return req<{ ok: boolean; model: string; status: string }>('/model/llm/local/pull', { method: 'POST', body: fd })
}

export interface LlmProviderInfo {
  name: string
  available: boolean
  requires_key: boolean
  key_configured: boolean
  default_model: string
  models: string[]
}

export interface LlmCatalog {
  provider: string
  model: string
  temperature: number
  local_endpoint: string
  providers: LlmProviderInfo[]
}

// ── Predict ─────────────────────────────────────────────────────────────────
export const predict = (smiles: string, top_n = 10) =>
  req<PredictResult>('/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ smiles, top_n }),
  })

export const comparePredictions = (smiles1: string, smiles2: string) =>
  req<ComparisonResult>('/predict/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ smiles1, smiles2 }),
  })

export const focusPredictionBit = (
  smiles: string,
  options: { bit_index?: number; mode?: 'strongest-negative' },
) =>
  req<FocusedPredictionResult>('/predict/focus-bit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ smiles, ...options }),
  })

export const getBitDatabaseInfo = (bitIndexOrMode: number | 'most-ambiguous' | 'top-active' | 'top-inactive') =>
  req<BitDatabaseInfo>(
    bitIndexOrMode === 'most-ambiguous'
      ? '/predict/bit-db/most-ambiguous'
      : bitIndexOrMode === 'top-active'
        ? '/predict/bit-db/top-active'
        : bitIndexOrMode === 'top-inactive'
          ? '/predict/bit-db/top-inactive'
      : `/predict/bit-db/${bitIndexOrMode}`,
  )

export const getActiveOnMostAmbiguousBit = (smiles: string) =>
  req<BitDatabaseInfo>('/predict/bit-db/active-on-most-ambiguous', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ smiles }),
  })

// ── Design ──────────────────────────────────────────────────────────────────
export const runDesign = (
  smiles: string,
  n_variants = 200,
  top_k = 9,
  w_activity = 0.50,
  w_diversity = 0.25,
  w_ad = 0.25,
  n_iterations = 5,
  beam_size = 3,
  n_per_iter = 100,
  patience = 3,
  use_druglikeness = true,
) =>
  req<DesignResult>('/design', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      smiles,
      n_variants,
      top_k,
      w_activity,
      w_diversity,
      w_ad,
      n_iterations,
      beam_size,
      n_per_iter,
      patience,
      use_druglikeness,
    }),
  })

// ── Molecule ─────────────────────────────────────────────────────────────────
export const moleculeImageUrl = (smiles: string, w = 300, h = 200) =>
  `${BASE}/molecule/image?smiles=${encodeURIComponent(smiles)}&width=${w}&height=${h}`

export const moleculeHighlightUrl = (
  smiles: string,
  atomIdx: number,
  radius: number,
  direction = 'active',
  w = 420,
  h = 300,
) =>
  `${BASE}/molecule/highlight?smiles=${encodeURIComponent(smiles)}&atom_idx=${atomIdx}&radius=${radius}&direction=${encodeURIComponent(direction)}&width=${w}&height=${h}`

export const validateSmiles = (smiles: string) =>
  req<{ valid: boolean; canonical: string | null }>(`/molecule/validate?smiles=${encodeURIComponent(smiles)}`)

export const getMoleculeDiff = (smiles_a: string, smiles_b: string) =>
  req<{
    added_frags: string[]
    removed_frags: string[]
    added_frag_labels?: string[]
    removed_frag_labels?: string[]
    fragment_render_warning?: string
    scaffold_change: boolean
  }>(
    `/molecule/diff?smiles_a=${encodeURIComponent(smiles_a)}&smiles_b=${encodeURIComponent(smiles_b)}`
  )

// ── Evaluate ─────────────────────────────────────────────────────────────────
export const getEvaluation = () => req<EvaluationResult>('/evaluate')

// ── Visualizer ───────────────────────────────────────────────────────────────
export const getVisualizerData = (
  page = 1, perPage = 48,
  filterClass: 'all' | 'active' | 'inactive' = 'all',
  sort: 'default' | 'prob_asc' | 'prob_desc' = 'default',
  search = '',
) =>
  req<VisualizerResult>(
    `/model/visualizer?page=${page}&per_page=${perPage}&filter_class=${filterClass}&sort=${sort}&search=${encodeURIComponent(search)}`,
  )

// ── Screening ────────────────────────────────────────────────────────────────
export const runScreening = (file: File, smiles_col = 'smiles') => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('smiles_col', smiles_col)
  return req<{ n_total: number; results: ScreeningRow[] }>('/screening', { method: 'POST', body: fd })
}

// ── Chat ─────────────────────────────────────────────────────────────────────
export async function* streamChat(message: string, use_rag = true, smiles_context?: string): AsyncGenerator<string> {
  const res = await fetch(BASE + '/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, use_rag, smiles_context }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? res.statusText)
  }
  if (!res.body) throw new Error('Chat stream did not return a response body')
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6)
      if (data === '[DONE]') return
      let parsed: { chunk?: string; error?: string }
      try {
        parsed = JSON.parse(data)
      } catch { continue }
      if (parsed.error) throw new Error(parsed.error)
      if (parsed.chunk) yield parsed.chunk
    }
  }
}

export const chatSimple = (message: string, use_rag = true, smiles_context?: string) =>
  req<{ response: string; pipeline_injected?: boolean }>('/chat/simple', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, use_rag, smiles_context }),
  })

// ── RAG ──────────────────────────────────────────────────────────────────────
export const addRagPdf = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return req<{ ok: boolean }>('/rag/add-pdf', { method: 'POST', body: fd })
}

// ── Types ────────────────────────────────────────────────────────────────────
export interface BitInfo {
  rank: number
  bit: string
  bit_index: number
  shap_value: number
  abs_shap: number
  direction: string
  bit_on: number
  molecule_substructures: { smiles: string; atom_idx: number; radius: number }[]
  training_info?: BitTrainingInfo | null
}

export interface BitTrainingInfo {
  substructures: Record<string, number>
  radii?: Record<string, number[]>
  active_freq: number
  inactive_freq: number
  total_activations: number
  n_unique_substructures: number
  dominant_substructure: string | null
  dominance: number
  is_ambiguous: boolean
  active_ratio: number
}

export interface ActiveBitInfo {
  bit: string
  bit_index: number
  molecule_substructures: { smiles: string; atom_idx: number; radius: number }[]
  training_info?: BitTrainingInfo | null
}

export interface PredictResult {
  smiles: string
  canonical_smiles: string
  prediction: 'Active' | 'Inactive'
  probability_active: number
  probability_inactive: number
  expected_value: number
  top_bits: BitInfo[]
  active_bits: ActiveBitInfo[]
  n_on_bits: number
  radius: number
  n_bits: number
}

export interface FocusedPredictionResult {
  prediction: PredictResult
  focus_bit: BitInfo
}

export interface ComparisonBitInfo {
  bit: string
  in_mol1: boolean
  in_mol2: boolean
  shap_mol1: number
  shap_mol2: number
  shap_diff: number
  mol_subs: { smiles: string; atom_idx: number; radius: number }[]
  db?: BitTrainingInfo | null
}

export interface ComparisonResult {
  identical?: boolean
  canonical_smiles?: string
  mol1: PredictResult
  mol2: PredictResult
  tanimoto: number
  bits_only_mol1: number
  bits_only_mol2: number
  bits_shared: number
  delta_probability: number
  top_differentiating_bits: ComparisonBitInfo[]
}

export interface BitDatabaseSubstructure {
  smiles: string
  count: number
  percentage: number
  radii?: number[]
}

export interface BitDatabaseInfo {
  bit: string
  bit_index: number
  total_activations: number
  active_freq: number
  inactive_freq: number
  active_ratio: number
  n_unique_substructures: number
  dominant_substructure: string | null
  dominance: number
  collision_confidence: {
    level: 'high' | 'moderate' | 'low'
    label: string
    is_severe: boolean
  }
  evidence_confidence?: {
    level: 'sufficient' | 'limited' | 'insufficient'
    label: string
    is_reliable: boolean
  }
  substructures: BitDatabaseSubstructure[]
  collision_scope: string
  molecule_context?: {
    canonical_smiles: string
    bit_on: boolean
    molecule_substructures: { smiles: string; atom_idx: number; radius: number }[]
  }
}

export interface DesignCandidate {
  smiles: string
  probability: number
  delta: number
  source: string
  transformation: string
  rank: number
  ad_score: number
  parent_smiles: string | null
  iteration: number
}

export interface HistoryStep {
  iteration: number
  n_generated: number
  best_prob: number
  ad_score: number
  best_smiles: string
}

export interface DesignResult {
  base_smiles: string
  base_probability: number
  n_generated: number
  n_valid: number
  candidates: DesignCandidate[]
  history: HistoryStep[]
  timeline_path: HistoryStep[]
  top_candidate_prob: number | null
  top_candidate_iteration: number | null
}

export interface EvaluationResult {
  roc_auc: number
  pr_auc: number
  confusion_matrix: number[][]
  roc_curve: { fpr: number[]; tpr: number[] }
  pr_curve: { precision: number[]; recall: number[] }
  n_active: number
  n_inactive: number
  imbalance_metrics?: ImbalanceMetrics | null
  test_roc_auc?: number | null
  test_pr_auc?: number | null
  test_confusion_matrix?: number[][] | null
  test_roc_curve?: { fpr: number[]; tpr: number[] } | null
  test_pr_curve?: { precision: number[]; recall: number[] } | null
  test_imbalance_metrics?: ImbalanceMetrics | null
  test_n_active?: number | null
  test_n_inactive?: number | null
}

export interface ImbalanceMetricValue {
  value: number | null
  ci: Array<number | null>
}

export interface ImbalanceMetrics {
  metrics: {
    average_precision: ImbalanceMetricValue
    brier_score: ImbalanceMetricValue
    ece: ImbalanceMetricValue
    ef_1: ImbalanceMetricValue
    ef_5: ImbalanceMetricValue
    ef_10: ImbalanceMetricValue
  }
  reliability: {
    mean_predicted: number[]
    observed_rate: number[]
  }
}

export interface VisualizerMolecule {
  index: number
  smiles: string
  label: number
  probability: number
}

export interface VisualizerResult {
  molecules: VisualizerMolecule[]
  total: number
  n_pages: number
  page: number
  n_active: number
  n_inactive: number
  accuracy: number
  hist_bins: number[]
  hist_active: number[]
  hist_inactive: number[]
}

export interface ScreeningRow {
  smiles: string
  valid: boolean
  probability: number | null
  prediction: string | null
}
