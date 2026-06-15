# Architecture Documentation — Molecular Feature Interpreter (MolChat)

> **Purpose.** This document provides a complete technical reference for the
> Molecular Feature Interpreter application, intended as the primary source
> for authoring the Methods section of a scientific publication.
> Every statement is derived directly from source code; no detail is assumed
> or extrapolated.

---

## 1. Overview

The Molecular Feature Interpreter (application title: *MolChat — Molecular AI
Interpreter*) is a web-based cheminformatics platform built on Streamlit that
accepts an externally trained binary-activity classification model and a
corresponding training dataset, and provides: (i) per-molecule activity
prediction with SHAP-based feature attribution at the fingerprint-bit level,
(ii) applicability-domain assessment, (iii) a retrieval-augmented generation
(RAG) chat interface that grounds LLM responses in computed molecular data,
(iv) a substructure activity search engine indexed against the training set,
(v) an iterative beam-search guided molecular design engine, and (vi) a
test-set evaluation module. The system is designed to be model-agnostic: any
scikit-learn–compatible estimator that exposes a `predict_proba()` method may
be uploaded; the platform then builds the SHAP explainer, applicability-domain
model, and fingerprint database automatically from the provided training data.

### 1.1 Technology Stack

| Library | Minimum version (from `requirements.txt`) |
|---|---|
| Python | Not specified in requirements (code uses `list[str]` type hints; Python ≥ 3.9 required) |
| streamlit | ≥ 1.28.0 |
| rdkit | ≥ 2024.3.0 |
| shap | ≥ 0.42.0 |
| scikit-learn | Not listed in `requirements.txt` (used extensively; version not determinable from source) |
| sentence-transformers | ≥ 2.2.0 |
| faiss-cpu | ≥ 1.7.4 |
| numpy | ≥ 1.24.0 |
| pandas | ≥ 2.0.0 |
| groq | ≥ 0.4.0 |
| openai | ≥ 1.0.0 |
| anthropic | ≥ 0.18.0 |
| PyPDF2 | ≥ 3.0.0 |
| joblib | ≥ 1.3.0 |
| pillow | ≥ 10.0.0 |
| python-dotenv | ≥ 1.0.0 |
| streamlit-ketcher | ≥ 0.0.3 |

### 1.2 Application Pages

Navigation is implemented via `st.pills` in the sidebar and maps to six
functional sections:

| Page label | Internal key | Description |
|---|---|---|
| Chat | `💬 Chat` | Conversational RAG interface; routes queries to specialized pipeline contexts |
| Visualizer | `🧬 ECFP/MACCS Visualizer` | Interactive display of ECFP bit states and MACCS key grid with substructure imagery |
| Prediction | `🔮 Prediction` | Per-molecule prediction, SHAP waterfall, AD assessment, SHAP-guided modification suggestions |
| Search | `🔍 Substructure Search` | Keyword-driven search of the training-set fingerprint database for substructure–activity correlations |
| Design | `🧪 Design` | Iterative beam-search guided molecular optimization with evolution path visualization |
| Evaluation | `📊 Evaluation` | Test-set performance metrics, ROC/PR curves, prediction distribution histogram, Murcko scaffold analysis |

---

## 2. Data

### 2.1 Input Format

Two CSV files may be uploaded by the user:

**Training CSV** — used to build the fingerprint database, applicability-domain
model, and aggregate statistics. Required columns (names are user-specified at
upload time):
- A SMILES column containing valid SMILES strings.
- A binary label column containing integer values `0` (inactive) and `1`
  (active).

Rows containing invalid SMILES are silently skipped during fingerprint
database construction; the number of skipped rows (`n_failed`) is returned by
`build_bit_database()` and reported to the user.

**Test CSV** — used exclusively by the Evaluation module. Required columns
match the training CSV (same user-specified SMILES and label column names).
After upload, predictions are appended as two additional columns:
`_pred_proba` (float, `predict_proba()[:, 1]`) and `_pred_label` (int,
threshold 0.5). The test set must contain at least 10 molecules for metrics
to be considered reliable (warning issued otherwise).

No column filtering or class-balance resampling is applied at load time beyond
SMILES validity checks.

### 2.2 Data Loading, Validation, and Session Persistence

Training data are loaded via `pandas.read_csv()` in the sidebar component.
Upon loading, the following derived objects are computed and stored in
`st.session_state`:
- The fingerprint matrix `X_train` (shape `[n_molecules, n_bits]`, `int32`).
- The label vector `y_train`.
- The SMILES list `smiles_train`.
- The bit database `bit_database` (see Section 3.4).
- Aggregate statistics `aggregate_stats` (see Section 3.5).
- The applicability-domain model `ad_model` (see Section 4.4).

**Persistence mechanism.** Session state is saved to and restored from a
single binary file, `.molchat_session.pkl`, located in the project root
directory (i.e., the same directory as `app.py`). The file format is Python
`pickle` with protocol 5 (`pickle.HIGHEST_PROTOCOL = 5` is used explicitly).
The session schema carries an integer version field (`_VERSION = 2`); sessions
with a lower version number are rejected on load to prevent schema mismatch
errors. The following keys are serialized verbatim:
`fp_radius`, `fp_nbits`, `fp_use_features`, `current_smiles`, `model_meta`,
`X_train`, `smiles_train`, `y_train`, `bit_database`, `bit_database_meta`,
`aggregate_stats`, `ad_model`, `test_df`, `test_df_meta`.
The fitted sklearn model is additionally serialized as raw bytes via
`pickle.dumps(model, protocol=5)` and stored under the key `model_bytes`.
The SHAP `TreeExplainer` object is serialized similarly under
`shap_explainer_bytes` (silently omitted if it is not pickle-serializable).
On restore, if `shap_explainer_bytes` is absent, the explainer is rebuilt from
the restored model via `shap.TreeExplainer(model)` at a one-time cost.
The metadata dict `bit_database_meta` (containing `n_molecules`, `n_bits_indexed`)
and `model_meta` (containing `filename`, `type`) are persisted for display in
the restore dialog without requiring a full deserialization.

---

## 3. Molecular Representation

### 3.1 Primary Fingerprint for Modeling

The primary fingerprint used for all prediction, applicability-domain
assessment, and SHAP analysis is the Extended Connectivity Fingerprint
(**ECFP6**), computed as a folded binary bit-vector via
`rdkit.Chem.AllChem.GetMorganFingerprintAsBitVect()` with the following
default parameters:

| Parameter | Default value | Session state key |
|---|---|---|
| radius | 3 (ECFP6 = 2 × radius) | `fp_radius` |
| nBits | 2048 | `fp_nbits` |
| useFeatures | False (connectivity-based, not FCFP) | `fp_use_features` |

These parameters are user-configurable in the sidebar and must match the
parameters used during model training. The bit-vector is converted to a
`numpy.ndarray` of dtype `int32` via
`rdkit.DataStructs.ConvertToNumpyArray()`.

When `bitInfo` collection is required (e.g., for substructure interpretation),
the same call is made with `bitInfo=bi` (a pre-allocated empty dict), which
maps each active bit index to a list of `(atom_idx, radius)` tuples identifying
the center atom and radius of every environment that hashes to that bit.

### 3.2 MACCS Keys

MACCS keys (166-bit Molecular ACCess System keys) are computed via
`rdkit.Chem.MACCSkeys.GenMACCSKeys()`, returning a 167-bit
`ExplicitBitVect` (bits 0–166; bit 0 is conventionally unused). MACCS keys
are used for the interactive Visualizer page and are not used in model training
or SHAP analysis. Per-key SMARTS patterns are retrieved at runtime from
`rdkit.Chem.MACCSkeys.smartsPatts`.

### 3.3 Additional Fingerprints (Visualization Only)

The `FingerprintEngine` class additionally implements — for exploratory
visualization only, not used in the prediction pipeline:
- **RDKit topological fingerprint** (`Chem.RDKFingerprint`, `minPath=1`,
  `maxPath=7`, `fpSize=2048`).
- **Atom-pair fingerprint** (`rdMolDescriptors.GetHashedAtomPairFingerprintAsBitVect`,
  `nBits=2048`).
- **Topological torsion fingerprint**
  (`rdMolDescriptors.GetHashedTopologicalTorsionFingerprintAsBitVect`,
  `nBits=2048`).

### 3.4 Physicochemical Descriptors

The `DescriptorCalculator` class exposes the complete set of RDKit descriptors
via `rdkit.ML.Descriptors.MoleculeDescriptors.MolecularDescriptorCalculator`.
The set of descriptors included in the standard physicochemical panel is:
`MolWt`, `ExactMolWt`, `HeavyAtomMolWt`, `LogP` (Crippen), `MR` (Crippen),
`TPSA`, `LabuteASA`, `NumHDonors`, `NumHAcceptors`, `NumRotatableBonds`,
`NumHeteroatoms`, `NumAromaticRings`, `NumSaturatedRings`, `NumAliphaticRings`,
`RingCount`, `FractionCSP3`, `NumHeavyAtoms`.
Lipinski Rule-of-Five compliance is assessed using the classical thresholds
(MW ≤ 500, logP ≤ 5, HBD ≤ 5, HBA ≤ 10); the number of violations is
reported alongside pass/fail status.

### 3.5 Fingerprint Bit Collision Database

At training time, a per-bit knowledge base is constructed by
`core.bit_database.build_bit_database()`. For each molecule in the training
set, `AllChem.GetMorganFingerprintAsBitVect()` is called with `bitInfo` enabled.
For every active bit, the atomic environment at each `(atom_idx, radius)` pair
is extracted as a canonical SMILES fragment via
`Chem.FindAtomEnvironmentOfRadiusN()` → `Chem.PathToSubmol()` →
`Chem.MolToSmiles()`. Multiple occurrences of the same environment within one
molecule (arising from molecular symmetry) are deduplicated before counting.

The resulting database maps each bit index to a dict containing:
`substructures` (Counter of `{env_smiles: count}`), `active_freq`,
`inactive_freq`, `total_activations`, `n_unique_substructures`,
`dominant_substructure` (most frequent by count), `dominance` (percentage of
activations covered by the dominant substructure), `is_ambiguous`
(`n_unique_substructures > 1`), and `active_ratio`
(`active_freq / total_activations`).

**Bit collision handling.** A bit is classified as ambiguous when multiple
chemically distinct substructures hash to the same folded index. The `dominance`
metric quantifies the severity: ≥ 80% → HIGH confidence; 50–80% → MODERATE;
< 50% → LOW (mixed signal). A WARNING is surfaced to the user when `dominance`
< 40%, because in this regime the SHAP value aggregates contributions from
multiple unrelated chemical environments and cannot be attributed to a single
substructure.

---

## 4. Model Pipeline

### 4.1 Algorithm

The model is not trained within the application; it is loaded from a file
uploaded by the user. Both `pickle` and `joblib` formats are supported
(attempted in that order). Any scikit-learn estimator that exposes
`predict_proba()` is accepted. The application is validated primarily with
tree-based ensemble models (Random Forest) because the SHAP module relies on
`shap.TreeExplainer`, which requires such estimators. Loading warnings arising
from scikit-learn version mismatches (`InconsistentVersionWarning`) are
suppressed.

The loaded estimator is stored in `st.session_state["rf_model"]`. Metadata
(filename, inferred type) are stored in `st.session_state["model_meta"]`.

### 4.2 Fingerprint Parameters

The fingerprint parameters used for prediction (Section 3.1) must be identical
to those used during external model training. The application stores these
in `st.session_state["fp_radius"]` (default 3) and
`st.session_state["fp_nbits"]` (default 2048).

### 4.3 Prediction and SHAP Attribution

The full prediction pipeline is implemented in
`core.model_pipeline.predict_and_interpret()`. The steps are:

1. **SMILES parsing** — `Chem.MolFromSmiles()`; returns an error dict on failure.
2. **Fingerprint** — `AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits)`;
   converted to `int32 ndarray` via `DataStructs.ConvertToNumpyArray()`.
3. **Prediction** — `model.predict_proba(fp.reshape(1, -1))[0]`; class 1
   (active) threshold is 0.5.
4. **SHAP values** — `explainer.shap_values(fp.reshape(1, -1))`. Output shape
   normalization handles three SHAP output conventions: list of arrays (one per
   class), 3-D array `[samples, features, classes]`, and 2-D array
   `[samples, features]`. In all cases, the class-1 (active) SHAP vector of
   length `n_bits` is extracted.
5. **bitInfo collection** — a second `GetMorganFingerprintAsBitVect()` call
   with `bitInfo` enabled maps each active bit to its atom environments.
6. **Top-N bits** — the `top_n` bits with highest `|SHAP|` are selected via
   `np.argsort(np.abs(shap_vals))[::-1][:top_n]`. Default `top_n = 10`.
7. **Per-bit annotation** — for each top bit, molecule-level substructures and
   training-set context (from `bit_db`) are attached.

The function returns the full fingerprint array and full SHAP vector as
`fp_array` and `shap_values_all` in addition to the per-bit summary, enabling
downstream modules (`comparison_pipeline`, `aggregate_stats`) to access
bit-level data without recomputing fingerprints.

The SHAP `TreeExplainer` is created once via
`shap.TreeExplainer(model)` and cached in `st.session_state["shap_explainer"]`
to avoid the ~1 s initialization cost on repeated queries.

The **expected value** (model baseline) is extracted from
`explainer.expected_value`; when it is a list or array (one per class), index 1
is used.

### 4.4 Applicability Domain

The applicability domain (AD) is assessed in `core.applicability_domain` using
a **k-nearest-neighbour** approach with **Jaccard (Tanimoto) distance** as the
similarity metric.

**AD model construction** (`build_ad_model(X_train)`):
1. A `sklearn.neighbors.NearestNeighbors` model is fitted on the training
   fingerprint matrix with `metric='jaccard'`, `n_neighbors=min(5, len(X_train))`,
   `n_jobs=-1`. The matrix is cast to `bool` before fitting.
2. `kneighbors()` is called on the training set itself to obtain the mean
   k-NN Jaccard distance per training molecule.
3. The AD threshold is defined as:

   ```
   threshold = mean(d_train) + 2 × std(d_train)
   ```

   where `d_train` is the vector of per-molecule mean k-NN distances over the
   training set.

**AD assessment** (`check_applicability_domain(smiles, ad_tuple, ...)`):
1. The query fingerprint is computed at the session parameters and converted
   to bool.
2. `kneighbors(X_query)` returns distances to the k nearest training neighbours.
3. `mean_knn_distance = mean(distances[0])`.
4. `inside_ad = mean_knn_distance ≤ threshold`.
5. **AD confidence** is classified as: HIGH if the molecule is inside AD and
   more than 30% below threshold; MODERATE if 10–30% below; LOW if ≤ 10%
   below; OUTSIDE AD (with percent overshoot) otherwise.
6. **Random Forest tree variance** — when the loaded model exposes
   `model.estimators_`, the standard deviation of per-tree `P(active)` values
   is computed as an independent uncertainty estimate.

**AD score for design** (`compute_ad_score`, `design_engine.py`): a separate,
simpler continuous score is used during iterative optimization. It is defined
as the mean Tanimoto similarity of the query fingerprint to its 5 nearest
training neighbours:

```
ad_score = mean(top-5 Tanimoto similarities to X_train)
```

Values near 1 indicate the molecule is well-represented in training chemical
space; values near 0 indicate high structural novelty relative to the training
set. This score is distinct from the binary AD flag described above and is used
as a soft reward term in beam selection (Section 7).

---

## 5. Explainability (SHAP)

### 5.1 Explainer

`shap.TreeExplainer` is used exclusively, as it is designed for tree-based
ensemble models and provides exact SHAP values (rather than approximate kernel
SHAP values) in a computationally tractable time. The explainer is initialized
as `shap.TreeExplainer(model)` and requires the model to be a tree-based
estimator (e.g., `RandomForestClassifier`).

### 5.2 Feature-Level Attribution

SHAP values are computed over the binary ECFP6 fingerprint vector. Each of the
`n_bits` (default 2048) fingerprint bits receives a SHAP value representing its
additive contribution to `log-odds(P(active))` relative to the model's expected
value (baseline). A positive SHAP value indicates the bit pushes the prediction
toward the active class; a negative value pushes it toward inactive.

### 5.3 Bit-to-Substructure Mapping

The mapping from fingerprint bit index to chemical substructure is performed at
two levels:

1. **Molecule-level** (query molecule only): `AllChem.GetMorganFingerprintAsBitVect()`
   is called with `bitInfo` enabled. For each `(atom_idx, radius)` pair
   associated with an active bit, the atomic environment is extracted as a
   canonical SMILES fragment via `Chem.FindAtomEnvironmentOfRadiusN()` →
   `Chem.PathToSubmol(atomMap=amap)` → `Chem.MolToSmiles()`. Symmetry
   duplicates (same canonical SMILES from different symmetric centers) are
   deduplicated before reporting.

2. **Training-level** (global context): the bit collision database (Section
   3.5) provides the distribution of all substructures that mapped to the same
   bit across the training set, together with their frequencies and the
   associated active/inactive ratios.

### 5.4 Bit Collision and Interpretation Confidence

For each top-SHAP bit, the `dominance` metric from the bit database is used to
qualify the reliability of the attribution. Three confidence levels are
reported: HIGH (dominance ≥ 80%), MEDIUM (50–80%), and LOW (< 50%). When
multiple chemically unrelated substructures share a bit (`n_unique_substructures
> 1`), the SHAP value reflects the aggregate contribution of all of them, and
a warning is displayed. Specifically, when `dominance < 40%`, the bit is
flagged as a MIXED SIGNAL because the SHAP contribution cannot be attributed
to a single substructure.

### 5.5 SHAP Context for the LLM

`core.model_pipeline.format_interpretation_context()` converts the
`predict_and_interpret()` output into a structured plain-text block that is
injected verbatim into the LLM prompt. The block contains: canonical SMILES,
prediction, P(active), P(inactive), expected value, fingerprint parameters,
and for each top-SHAP bit: SHAP value, direction, bit ON/OFF status,
molecule-level substructures, and training-set frequency and active-ratio data.
The LLM is instructed to answer only from this grounded context.

### 5.6 Features Pushing Toward ACTIVE / INACTIVE

In the Prediction page, bits are ranked by absolute SHAP value and split into
two groups: positive SHAP (push toward ACTIVE) and negative SHAP (push toward
INACTIVE). For each group, the dominant substructure from the bit database is
displayed alongside the SHAP value, active ratio, and collision confidence
indicator.

The `core.suggestion_pipeline.suggest_modifications()` function further
classifies bits from the top-20 SHAP analysis into four action types:
- **REMOVE**: bit ON, SHAP < −0.001 (substructure present and penalizing
  activity).
- **ADD**: bit OFF, SHAP < −0.001 (absence of a favorable substructure is
  penalizing).
- **KEEP**: bit ON, SHAP > +0.001 (substructure present and beneficial).
- **CONSIDER**: bit absent in query but found in > 90% of active training
  molecules (`active_exclusive_bits` from aggregate stats).

ADD and REMOVE suggestions are computationally validated: `AllChem.DeleteSubstructs()`
or `Chem.CombineMols()` + `RWMol.AddBond()` is applied, the fingerprint is
recomputed, and the suggestion is accepted only if the target bit actually
changes state. The `predict_proba()` of the modified molecule is computed to
report the expected ΔP(active), and the AD status of the modified molecule is
checked against the AD model. At most 2 validated REMOVE and 2 validated ADD
suggestions are returned per molecule.

---

## 6. RAG Pipeline (Molecular Feature Interpreter)

### 6.1 Embedding Model

Text embeddings are generated by the `sentence-transformers` library using the
model **`all-MiniLM-L6-v2`** (default; overridable via the `EMBEDDING_MODEL`
environment variable). Embeddings are L2-normalized at generation time
(`normalize_embeddings=True`), enabling inner product to serve as cosine
similarity. The embedding dimension is not explicitly hardcoded; it is queried
at runtime via `model.get_sentence_embedding_dimension()`.

### 6.2 Vector Store

The vector store is implemented in `rag.vector_store.VectorStore` using the
**FAISS `IndexFlatIP`** (flat inner product) index. This index performs exact
nearest-neighbour search with no quantization or approximation. Embeddings are
stored as `float32`. The index, document chunks (as JSON), and metadata are
persisted to disk under `data/rag_index/` (path: `settings.rag_index_dir`).

### 6.3 Document Chunking

Documents (plain text, Markdown, PDF via `PyPDF2.PdfReader`) are chunked by
`rag.document_processor.DocumentProcessor` with:
- `chunk_size = 500` characters (default; overridable via `CHUNK_SIZE`
  environment variable).
- `chunk_overlap = 50` characters (default; overridable via `CHUNK_OVERLAP`).

Chunking is sentence-aware: text is first split on sentence boundaries
(`(?<=[.!?])\s+`), then sentences are accumulated until the target chunk size
is reached. The overlap is implemented by retaining the last N characters of
the preceding chunk as the prefix of the next chunk, taken as complete
sentences. Chunks shorter than `min_chunk_size = 100` characters are discarded.

PDF pages are extracted as plain text via `PdfReader.pages[i].extract_text()`
with page-number markers prepended.

### 6.4 Query Pipeline

On each user query, `rag.retriever.Retriever.retrieve()` is called:
1. The query string is embedded with `EmbeddingGenerator.embed_single()`.
2. `index.search(query_embedding, top_k=5)` returns the 5 most similar chunks
   by inner product (cosine similarity for normalized vectors).
3. The retrieved chunk texts are concatenated with double newlines to form the
   RAG context block.
4. The context is formatted and injected into the LLM prompt via
   `llm.prompt_templates.PromptTemplates.format_rag_prompt()`.

There is no re-ranking or score-threshold filtering applied beyond the FAISS
nearest-neighbour search. A `min_score` parameter exists in the API
(`search()` accepts `min_score=0.0` by default) but is not set to a non-zero
value in the standard retrieval path.

### 6.5 Multi-Provider LLM Support

Three LLM providers are supported via `llm.client_factory.LLMClientFactory`:

| Provider | Default model | SDK class |
|---|---|---|
| **Groq** (default) | `llama-3.3-70b-versatile` | `groq.Groq` |
| OpenAI | `gpt-4o-mini` | `openai.OpenAI` |
| Anthropic | `claude-3-5-sonnet-20241022` | `anthropic.Anthropic` |

Available Groq models: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`,
`qwen/qwen3-32b`. Available OpenAI models: `gpt-4o`, `gpt-4o-mini`,
`gpt-4-turbo`, `gpt-3.5-turbo`. Available Anthropic models:
`claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`, `claude-3-haiku-20240307`.

Provider switching is handled at the `ChatHandler` level: a new
`LLMClientFactory.create(provider, api_key, model)` instance is created
whenever the provider or model selection changes (detected by comparing
`st.session_state["last_provider"]` and `st.session_state["last_model"]`).
All providers support both synchronous and streaming (`stream=True`) generation.
The Anthropic client extracts the system message from the message list and
passes it via the dedicated `system=` parameter, as required by the
`anthropic.messages.create()` API.

Default generation parameters: `temperature = 0.7`, `max_tokens = 4096`.

### 6.6 Query Routing

Incoming chat messages are classified by `core.query_router.classify_query()`
into one of nine typed categories, processed in priority order:

| Priority | Type | Trigger condition |
|---|---|---|
| 1 | `comparison` | Two distinct valid SMILES detected in the query |
| 2 | `bit_query` | ECFP bit pattern (`ecfpN_NNN`, `bit NNN`, etc.) without accompanying SHAP value |
| 3 | `ad_check` | AD/reliability keywords |
| 4 | `mol_edit` | Edit-intent keywords AND one valid SMILES |
| 5 | `design_query` | Design/variant-generation keywords |
| 5 | `suggestions` | Optimization-intent keywords AND one valid SMILES |
| 6 | `substructure_search` | Named functional group or structure-activity keywords |
| 7 | `aggregate_query` | Dataset-level statistical keywords |
| 8 | `molecule_query` | Any valid SMILES present |
| 9 | `general_query` | Fallback |

SMILES detection uses a two-tier strategy: (1) quoted strings (highest
confidence), then (2) unquoted tokens that contain at least one non-alphabetic
character (RDKit SMILES always contain brackets, digits, `=`, `#`, etc.). Pure
alphabetic tokens are never passed to `Chem.MolFromSmiles()`.

---

## 7. Guided Molecular Design Pipeline

### 7.1 Entry Point

The guided pipeline is invoked via `core.design_engine.run_guided_pipeline()`.
Signature (key parameters):

```python
run_guided_pipeline(
    smiles: str,
    model: Any,
    radius: int = 3,
    n_bits: int = 2048,
    n_variants_per_iter: int = 100,
    n_iterations: int = 5,
    beam_size: int = 3,
    dataset_fps: Optional[np.ndarray] = None,
    train_smiles: Optional[list] = None,
    top_k: int = 9,
    patience: int = 3,
    shap_explainer: Any = None,
    bit_db: Optional[dict] = None,
    w_prob: float = 0.50,
    w_div: float = 0.25,
    w_ad: float = 0.25,
    use_druglikeness: bool = True,
    preserve_core: bool = True,
    progress_callback = None,
) -> dict
```

### 7.2 Generation Strategies

Variant generation is centralized in `generate_variants_cross()`, which pools
contributions from six strategies:

**A. Cross-BRICS recombination** (`"brics_cross"`): BRICS fragments from all
beam molecules are pooled into a single fragment library.
`rdkit.Chem.BRICS.BRICSDecompose()` decomposes each beam molecule; fragments
are shuffled randomly; `BRICS.BRICSBuild()` enumerates recombined structures.
Budget: `min(n_variants // 2, 120)` variants. This is the primary source of
scaffold-level diversity.

**B. Per-molecule standard variants** (`"standard"`): single-molecule
`generate_variants()` is applied to each beam member, combining:
- BRICS self-recombination (same molecule decomposed and rebuilt).
- Atom substitution: systematic SMILES string-level replacement of halogen and
  heteroatom symbols, drawn from the `_ATOM_SWAPS` table
  (`Cl↔F`, `Cl↔Br`, `Cl↔I`, `F↔Br`, `F↔I`, `Br↔F`, `O↔S`, `S↔O`),
  up to 5 substitutions per swap type per molecule.
- Substituent attachment: small fragments from `_SUBSTITUENTS`
  (`F`, `Cl`, `C`, `OC`, `N`, `C(F)(F)F`, `C#N`, `C(=O)N`, `S(=O)(=O)N`,
  `C(=O)O`) are bonded to aromatic carbons bearing free hydrogens
  (up to 4 attachment sites per molecule).

**C. Ring bioisosteres** (`"bioisostere"`): aromatic C atoms not in
`protected_atoms` and not at ring junctions are replaced by N
(`SetAtomicNum(7)`) to generate ring-nitrogen bioisosteric analogues
(e.g., benzene → pyridine).

**D. Terminal group removal** (`"terminal_removal"`): terminal heavy atoms
(degree 1, not hydrogen, not in `protected_atoms`) are removed one at a time
via `RWMol.RemoveAtom()`, sorted by atomic number for determinism.

**E. SHAP-guided modifications** (`"shap_guided"`): available only when a
`TreeExplainer` and `bit_db` are provided. SHAP values are computed on the
batch of beam molecules. For each beam molecule:
- **Pro-activity bits** (SHAP > 0, bit currently OFF): up to 10 such bits are
  identified; the dominant substructure from `bit_db` is attached to available
  aromatic carbons; only variants where the target bit actually flips ON are
  retained.
- **Anti-activity bits** (SHAP < 0, bit currently ON): up to 5 such bits;
  the dominant substructure is deleted via `Chem.DeleteSubstructs()`; only
  variants where the target bit actually flips OFF are retained.
Budget: `n_variants // 4`.

**F. Peripheral decoration** (`"peripheral"`): when `preserve_core=True`,
substituents from `_PERIPHERAL_SUBSTITUENTS` (15 fragments: `F`, `Cl`, `C`,
`CC`, `O`, `OC`, `N`, `C(F)(F)F`, `C#N`, `C(=O)N`, `S(=O)(=O)N`, `OC(F)(F)F`,
`CC(C)C`, `c1ccncc1`, `c1ccccc1`) are attached exclusively to non-protected
peripheral atoms (aromatic or sp3 C/N with implicit H, not in
`protected_atoms`). Budget: `n_variants // 5`.

All candidates are deduplicated by canonical SMILES (`seen` set, updated
in-place across strategies and iterations).

### 7.3 Pharmacophore-Aware Generation

When `preserve_core=True`, a per-molecule protected atom set is computed by
`identify_protected_atoms(mol, explainer, radius, n_bits)`:

1. **Murcko scaffold atoms**: `MurckoScaffold.GetScaffoldForMol()` identifies
   the ring-and-linker scaffold; matched atom indices are always protected.
2. **SHAP-positive atoms**: the top 25% of ON bits with positive SHAP values
   are identified; for each such bit, only the *center atom*
   (`atom_idx` from `bitInfo`) is added to the protected set (not the full
   radius-N neighborhood), keeping the set focused.
3. **Hard cap**: if the combined set exceeds 70% of total heavy atoms, the
   function falls back to Murcko-only protection to ensure at least 30% of
   positions remain mutable.

A **post-hoc scaffold preservation filter** is applied after generation:
`core_preserved(child_mol, parent_cores)` checks that each generated molecule
contains at least one Murcko scaffold of the beam members as a substructure
(via `HasSubstructMatch()`). If all candidates fail this check, the filter is
bypassed to prevent pipeline stalls.

### 7.4 Drug-likeness Filter

An extended Lipinski filter is applied before beam selection when
`use_druglikeness=True`. The strict tier requires all five of:
150 ≤ MW ≤ 650, −2.0 ≤ logP ≤ 6.0, 0 ≤ HBA ≤ 12, 0 ≤ HBD ≤ 7,
0 ≤ RotB ≤ 12. If no candidate passes the strict tier, a relaxed fallback
(MW ≤ 800, logP ≤ 7.0) is applied. If no candidate passes the relaxed tier
either, all candidates are retained to prevent pipeline stalls.

### 7.5 Beam Search: MMR Selection

Beam selection is performed by `_diverse_beam_select()` using a
**Maximal Marginal Relevance** (MMR) formulation that integrates three terms:
predicted activity, structural diversity, and applicability domain:

```
Score(v) = w_prob × [P(v) / max_P]
         + w_div  × [1 − max_j∈S Tanimoto(fp_v, fp_j)]
         + w_ad   × [AD(v) / max_AD]
```

where S is the set of already-selected beam members, `P(v)` is
`predict_proba(v)[:, 1]`, and `AD(v)` is the continuous AD score (Section 4.4).
Default weights: `w_prob = 0.50`, `w_div = 0.25`, `w_ad = 0.25`.

The first beam member is selected greedily (no diversity penalty); subsequent
members are selected iteratively by maximizing the full three-term score. All
Tanimoto computations use the `float32` fingerprint arrays: `intersection =
fp_v · fp_j`, `union = sum(fp_v) + sum(fp_j) − intersection`.

Before beam selection, the `top_check` pool is formed by taking the top
`max(beam_size × 8, 40)` candidates by raw predicted probability. AD scores
are pre-computed for this filtered pool, avoiding full-dataset AD scoring.

### 7.6 Early Stopping

The pipeline tracks the number of consecutive non-improving iterations
(`_no_improve`). An iteration is considered non-improving if the global best
P(active) increases by less than `1e-4`. When `_no_improve ≥ patience`
(default: `patience = 3`), the pipeline logs the early-stop reason and
terminates. The history list still contains the final state, and the
visualization module truncates trailing repeated steps (Section 8.3).

### 7.7 Training Set Exclusion

At pipeline initialization, each training SMILES is canonicalized via
`Chem.MolToSmiles(Chem.MolFromSmiles(smi))` and added to a set
`_train_set`. At each iteration, generated candidates whose canonical SMILES
appear in `_train_set` are excluded from both the beam and the returned
results. In the edge case where all candidates in a given iteration belong to
the training set, the single best candidate is retained as fallback to prevent
the beam from collapsing.

### 7.8 Output

`run_guided_pipeline()` returns a dict containing:
`base_smiles`, `base_prob`, `candidates` (all unique novel molecules across
all iterations as `DesignCandidate` objects), `top_improvers` (top-k by ΔP),
`top_total` (top-k by absolute P(active)), `n_generated` (total molecules
evaluated), `history` (one dict per iteration; see Section 8), `guided`
(True).

---

## 8. Molecular Evolution Path Visualization

### 8.1 Overview

The evolution path is rendered by `ui.molecular_evolution_path.render_evolution_path()`.
It displays the sequence of best-scoring molecules from each beam search
iteration as a wrapped horizontal timeline, with structural transition
annotations between consecutive steps.

### 8.2 Top-1 Selection

The timeline uses the `best_smiles` field from each `history` entry, which is
the single highest-P(active) molecule across all novel candidates at that
iteration (the global best at iteration `i`, not the beam top-1).

### 8.3 Early Stopping Truncation

Before rendering, `_truncate_early_stopping()` scans for the first occurrence
of two consecutive identical canonical SMILES in the history list and
truncates the timeline at that point. This removes the visual noise of repeated
identical molecules caused by early stopping. The function uses canonical SMILES
comparison (`Chem.MolToSmiles(Chem.MolFromSmiles(s))`) with a plain-string
fallback on RDKit failure. When truncation occurs, a note is appended below the
timeline.

### 8.4 Structural Diff via MCS

Between each consecutive pair of timeline molecules, a structural diff is
computed by `compute_structural_diff()` using
`rdkit.Chem.rdFMCS.FindMCS([mol_a, mol_b], timeout=5)`.

- If `FindMCS` fails, is canceled, or returns 0 atoms, the transition is
  labeled as a **scaffold change**.
- If `mcs.numAtoms / min(mol_a.GetNumAtoms(), mol_b.GetNumAtoms()) < 0.40`,
  the transition is also labeled as a scaffold change (less than 40% of the
  smaller molecule is shared, indicating a major structural reorganization).
- Otherwise, `_non_mcs_frags()` identifies non-MCS atoms in each molecule
  via `GetSubstructMatch(mcs_mol)` + `MolFragmentToSmiles()`, producing
  **added fragments** (in mol_b but not mol_a) and **removed fragments** (in
  mol_a but not mol_b). At most 3 fragments per side are returned.

The MCS result is cached via `@st.cache_data`.

### 8.5 Layout

The timeline wraps at `_ROW_SIZE = 5` molecules per row. Molecule image sizes
adapt to the total number of steps: ≤ 3 steps: 250 × 200 px molecules,
108 × 90 px fragment boxes; ≤ 6 steps: 180 × 150 / 108 × 90; > 6 steps:
130 × 110 / 78 × 66. Images are rendered via `rdkit.Chem.Draw.MolToImage()`.
The timeline is rendered as an HTML table injected into the Streamlit app via
`st.markdown(html, unsafe_allow_html=True)`.

---

## 9. Evaluation Module

### 9.1 Performance Metrics

The following classification metrics are computed in
`ui.evaluation_page._render_metrics_section()` using scikit-learn:

| Metric | sklearn function |
|---|---|
| ROC-AUC | `roc_auc_score(y_true, y_proba)` |
| Precision | `precision_score(y_true, y_pred, zero_division=0)` |
| Recall (Sensitivity) | `recall_score(y_true, y_pred, zero_division=0)` |
| Specificity | `TN / (TN + FP)` from `confusion_matrix(y_true, y_pred).ravel()` |
| F1 Score | `f1_score(y_true, y_pred, zero_division=0)` |
| Matthews Correlation Coefficient | `matthews_corrcoef(y_true, y_pred)` |
| Balanced Accuracy | `balanced_accuracy_score(y_true, y_pred)` |

The classification threshold is fixed at 0.5 (`y_pred = (y_proba ≥ 0.5).astype(int)`).

### 9.2 Plots

- **ROC curve**: `roc_curve(y_true, y_proba)` → FPR/TPR, with the operating
  point at threshold = 0.5 marked. Generated via matplotlib.
- **Precision-Recall curve**: `precision_recall_curve(y_true, y_proba)` +
  `average_precision_score(y_true, y_proba)` (area under PR curve = AP).
  Generated via matplotlib.
- **Prediction distribution histogram**: 20 equal-width bins over [0, 1];
  overlapping histograms for active (n=active) and inactive (n=inactive) test
  molecules by their predicted P(active). A dashed line marks the 0.5 decision
  threshold. Generated via matplotlib.

### 9.3 Scaffold Analysis

Murcko scaffolds are computed for each test molecule via
`rdkit.Chem.Scaffolds.MurckoScaffold.GetScaffoldForMol()`, which extracts the
ring system and linker atoms. Molecules are grouped by canonical scaffold SMILES.
Only scaffolds with ≥ 2 molecules are included in the analysis.

Scaffold statistics computed per group: `total_count`, `active_count`,
`mean_pred_proba`, `active_rate = active_count / total_count`. Groups are
sorted by `active_rate` descending, then by `active_count` descending.
The function is cached via `@st.cache_data` keyed on the DataFrame hash.

---

## 10. Session State and Persistence

### 10.1 Session State Keys

The following keys are used in `st.session_state` across the application:

| Key | Type | Purpose |
|---|---|---|
| `app_initialized` | bool | Guards one-time initialization block |
| `llm_provider` | str | Selected LLM provider (`"groq"` / `"openai"` / `"anthropic"`) |
| `llm_model` | str | Selected model name (default: `"llama-3.3-70b-versatile"`) |
| `temperature` | float | LLM sampling temperature (default: 0.7) |
| `last_provider` | str | Provider at last ChatHandler initialization |
| `last_model` | str | Model at last ChatHandler initialization |
| `chat_handler` | `ChatHandler` | Active LLM chat handler object |
| `retriever` | `Retriever` | Active RAG retriever (FAISS index) |
| `current_smiles` | str | SMILES of the currently active molecule |
| `fp_radius` | int | Morgan fingerprint radius (default: 3) |
| `fp_nbits` | int | Fingerprint bit count (default: 2048) |
| `fp_use_features` | bool | Use feature-based FCFP (default: False) |
| `rf_model` | sklearn estimator | Loaded classification model |
| `shap_explainer` | `shap.TreeExplainer` | SHAP explainer (cached) |
| `model_meta` | dict | Model metadata (`filename`, `type`) |
| `X_train` | `ndarray[n×d, int32]` | Training fingerprint matrix |
| `smiles_train` | list[str] | Training SMILES strings |
| `y_train` | array | Training labels (binary) |
| `bit_database` | dict | Per-bit collision database from `build_bit_database()` |
| `bit_database_meta` | dict | Metadata: `n_molecules`, `n_bits_indexed` |
| `aggregate_stats` | dict | Dataset-level statistics from `build_aggregate_stats()` |
| `ad_model` | tuple | AD model: `(knn, threshold, train_mean, train_std)` |
| `test_df` | `pd.DataFrame` | Test set with `_pred_proba`, `_pred_label` columns |
| `test_df_meta` | dict | Test set metadata: `smiles_col`, `label_col` |
| `design_n_variants` | int | Variants per iteration for beam search (default: 200) |
| `current_structures` | list[dict] | Structures referenced in current chat turn |
| `design_smiles_input_pending` | str | SMILES to load into design input (from evolution path) |
| `_design_canonical_train` | set[str] | Canonical SMILES of training set (design cache) |
| `_design_cache` | dict | Cached design results |

### 10.2 Persistence to Disk vs. In-Memory Only

**Persisted to `.molchat_session.pkl`**: `fp_radius`, `fp_nbits`,
`fp_use_features`, `current_smiles`, `model_meta`, `X_train`, `smiles_train`,
`y_train`, `bit_database`, `bit_database_meta`, `aggregate_stats`, `ad_model`,
`test_df`, `test_df_meta`, `rf_model` (as bytes), `shap_explainer` (as bytes,
optional).

**In-memory only (not persisted)**: `chat_handler`, `retriever`,
`current_structures`, `app_initialized`, `last_provider`, `last_model`,
`design_n_variants`, design caches, and all UI-ephemeral keys.

### 10.3 Save/Load Functions

| Function | File | Description |
|---|---|---|
| `save_session(session_state)` | `core/session_persistence.py` | Serializes selected keys to `.molchat_session.pkl` (pickle, protocol 5); returns `True` on success |
| `load_session(session_state)` | `core/session_persistence.py` | Restores keys from file; rejects version < 2; rebuilds SHAP explainer if bytes absent; invalidates design caches |
| `session_exists()` | `core/session_persistence.py` | Returns `True` if `.molchat_session.pkl` exists |
| `delete_session()` | `core/session_persistence.py` | Removes the session file (`unlink(missing_ok=True)`) |
| `peek_session_meta()` | `core/session_persistence.py` | Reads and returns the lightweight metadata dict without fully deserializing session objects |

---

## 11. File and Module Map

| File/Module | Purpose | Key functions/classes |
|---|---|---|
| `app.py` | Main Streamlit entry point; page routing, LLM/RAG initialization, session restore dialog | `init_app()`, `init_llm()`, `init_retriever()`, `_show_restore_dialog()` |
| `config/settings.py` | Application-wide settings dataclass; reads from environment variables | `Settings`, `settings` (global instance) |
| `config/api_config.py` | API key configuration helpers | `APIConfig`, `api_config` |
| `core/model_pipeline.py` | SMILES → fingerprint → prediction → SHAP → structured context | `predict_and_interpret()`, `load_model()`, `create_explainer()`, `format_interpretation_context()` |
| `core/fingerprint_engine.py` | Multi-type fingerprint generation (ECFP, MACCS, RDKit, AtomPair, TopTorsion) | `FingerprintEngine`, `FingerprintResult` |
| `core/applicability_domain.py` | kNN Jaccard AD model construction and query assessment | `build_ad_model()`, `check_applicability_domain()`, `format_ad_context()` |
| `core/descriptor_calculator.py` | RDKit physicochemical, Lipinski, topological descriptor calculation | `DescriptorCalculator` |
| `core/molecule_parser.py` | SMILES parsing, validation, canonicalization | `MoleculeParser`, `MoleculeInfo` |
| `core/bit_database.py` | Per-bit fingerprint collision database construction and query | `build_bit_database()`, `get_molecule_bit_info()`, `get_bit_context()`, `format_bit_context_for_llm()` |
| `core/aggregate_stats.py` | Dataset-level statistics over the bit database (active-exclusive bits, collision rates) | `build_aggregate_stats()`, `select_aggregate_context()` |
| `core/suggestion_pipeline.py` | SHAP-based structural modification suggestions; substructure activity search | `suggest_modifications()`, `search_substructure_activity()`, `validate_add_suggestion()`, `validate_remove_suggestion()` |
| `core/molecular_editor.py` | Rule-based molecular editing via SMILES string substitution | `apply_edit_rdkit()`, `format_edit_context()` |
| `core/comparison_pipeline.py` | Side-by-side SHAP and fingerprint comparison of two molecules | `compare_molecules()`, `format_comparison_context()` |
| `core/query_router.py` | Query classification into typed categories for pipeline routing | `classify_query()`, `extract_smiles()`, `detect_two_smiles()` |
| `core/session_persistence.py` | Pickle-based session save/load to disk | `save_session()`, `load_session()`, `session_exists()`, `delete_session()`, `peek_session_meta()` |
| `core/design_engine.py` | Iterative beam-search guided molecular optimization with six generation strategies | `run_guided_pipeline()`, `generate_variants_cross()`, `generate_variants()`, `_diverse_beam_select()`, `identify_protected_atoms()`, `core_preserved()`, `compute_ad_score()`, `passes_druglikeness()`, `DesignCandidate` |
| `core/substructure_highlighter.py` | Substructure highlighting utilities | Not read in detail |
| `rag/retriever.py` | High-level RAG retriever: document ingestion, query, context formatting | `Retriever`, `RetrievalResult`, `create_chemistry_retriever()` |
| `rag/vector_store.py` | FAISS `IndexFlatIP` vector store with JSON chunk persistence | `VectorStore`, `SearchResult` |
| `rag/embeddings.py` | Sentence-transformer embedding generation (`all-MiniLM-L6-v2`) | `EmbeddingGenerator` |
| `rag/document_processor.py` | Text/PDF chunking with sentence-aware overlap | `DocumentProcessor`, `DocumentChunk`, `ProcessedDocument` |
| `llm/chat_handler.py` | Conversation management, multi-provider chat, RAG query with context | `ChatHandler`, `Conversation`, `Message` |
| `llm/client_factory.py` | Multi-provider LLM client factory (Groq, OpenAI, Anthropic) | `LLMClientFactory`, `OpenAIClient`, `AnthropicClient` |
| `llm/groq_client.py` | Groq API client with sync and streaming | `GroqClient`, `LLMResponse` |
| `llm/prompt_templates.py` | System prompts and per-task prompt formatters | `PromptTemplates` |
| `descriptors/descriptor_registry.py` | Registry mapping descriptor names to metadata | Not read in detail |
| `descriptors/descriptor_explainer.py` | LLM-assisted descriptor explanation | Not read in detail |
| `descriptors/extreme_finder.py` | Identifies molecules with extreme descriptor values in the training set | Not read in detail |
| `descriptors/maccs_descriptions.py` | Human-readable MACCS key descriptions (lookup dict) | `MACCS_DESCRIPTIONS` |
| `fingerprints/ecfp_interpreter.py` | Bit-level ECFP environment extraction and display | Not read in detail |
| `fingerprints/maccs_interpreter.py` | MACCS key matching and display | Not read in detail |
| `fingerprints/maccs_keys.py` | MACCS key definitions (SMARTS, description, category) for keys 1–166 | `MACCSKeyDefinition`, `MACCSKeys`, `MACCS_DEFINITIONS` |
| `ui/app.py` | *(not present; routing is in root `app.py`)* | — |
| `ui/sidebar.py` | Sidebar: navigation, LLM/model settings, SMILES input, training/test CSV upload | `Sidebar` |
| `ui/chat_interface.py` | Scrollable chat UI with special command routing and RAG integration | `ChatInterface` |
| `ui/prediction_page.py` | Prediction page: SHAP waterfall, AD badge, modification suggestions | Not read in detail |
| `ui/visualizer_page.py` | ECFP/MACCS Visualizer page | Not read in detail |
| `ui/design_panel.py` | Design page UI: parameter controls, design execution, results table | Not read in detail |
| `ui/molecular_evolution_path.py` | Molecular evolution path HTML timeline visualization | `render_evolution_path()`, `compute_structural_diff()`, `_truncate_early_stopping()` |
| `ui/evaluation_page.py` | Evaluation page: metrics, ROC/PR curves, distribution histogram, scaffold analysis | `render_evaluation_page()`, `_compute_scaffold_stats()` |
| `ui/substructure_page.py` | Substructure activity search page | Not read in detail |
| `ui/structure_panel.py` | Referenced-structures viewer (structures mentioned in chat) | `StructurePanel` |
| `ui/components.py` | Shared rendering components: MACCS grid, ECFP grid, bit detail, prediction card, AD badge | `render_maccs_grid()`, `render_maccs_detail()`, `render_ecfp_grid()`, `render_bit_detail()`, `render_prediction_card()`, `render_ad_badge()` |
| `ui/styles.py` | Global CSS injection | `Styles.get_css()` |
| `ui/clipboard.py` | Clipboard utility | Not read in detail |

---

## 12. Additional Methodological Details Relevant to a Scientific Paper

### 12.1 Grounded LLM Responses

A core design principle is that all LLM responses concerning molecular
predictions are grounded in computed data rather than the model's parametric
knowledge. The pipeline injects structured text blocks — containing actual
SHAP values, substructure SMILES, active ratios, AD distances, and training
frequencies — directly into the LLM user message via the respective
`format_*_context()` functions. A `system_override` parameter in
`ChatHandler.simple_query()` can replace the default system prompt with a
stricter, context-only instruction for calls that must not hallucinate
(e.g., MACCS key explanations).

### 12.2 Deduplication by Canonical SMILES

All molecular deduplication throughout the pipeline (fingerprint database
construction, design variant pool, training-set exclusion filter, SMILES
symmetry in bit environments) uses RDKit canonical SMILES
(`Chem.MolToSmiles(mol, canonical=True)`) as the unique molecular identifier.

### 12.3 Substructure Activity Search Algorithm

The `search_substructure_activity()` function in `core.suggestion_pipeline`
implements a three-tier fragment-matching strategy against the bit database:
(1) Tier-1 — single-atom symbol matching (reliable for halogens, N, O, S);
(2) Tier-2 — SMARTS `HasSubstructMatch()` for multi-atom fragments;
(3) Tier-3 — string containment fallback when no compiled matchers are
available. Only bits where at least one substructure entry *itself* contains
the queried fragment are returned; bits are not reported based on global
`active_ratio` alone. Results are sorted by `active_ratio` descending, and an
aggregate verdict is reported: strongly active-associated (mean active ratio ≥
0.75), moderately active-associated (0.55–0.75), mixed (0.45–0.55), moderately
inactive-associated (0.25–0.45), strongly inactive-associated (≤ 0.25).

### 12.4 Molecule Comparison Pipeline

`core.comparison_pipeline.compare_molecules()` computes a side-by-side
SHAP-annotated structural diff between two molecules. The Tanimoto similarity
is computed directly from the binary fingerprint arrays:
`|A ∩ B| / |A ∪ B|`. Differentiating bits (bits present in one molecule but
not both) are ranked by `|shap_mol2 − shap_mol1|`, and the top 15 are
reported with their substructure annotations and training-set context.

### 12.5 Bit Environment Extraction at Radius 0

When `radius = 0` in `_extract_env_smiles()`, the function returns the atom
symbol of the center atom directly (`mol.GetAtomWithIdx(atom_idx).GetSymbol()`),
bypassing `FindAtomEnvironmentOfRadiusN()` which would return an empty
environment at radius 0.

### 12.6 Lipinski Filter Bounds in the Design Pipeline

The design pipeline uses a *non-standard* Lipinski-extended filter that is
more permissive than the classical Ro5: MW 150–650 (vs. ≤ 500), logP −2 to
+6 (vs. ≤ 5), HBA 0–12 (vs. ≤ 10), HBD 0–7 (vs. ≤ 5), and an additional
RotB ≤ 12 constraint. This broader window is intended to accommodate fragment
growth from small seed molecules.

---

*Document generated from source-code reading of all modules in
`C:/Users/vince/Desktop/descriptos_app`. Files explicitly read: 30+ `.py`
files covering all core, RAG, LLM, UI, fingerprint, and descriptor modules.
Files for which only signatures/names were read (insufficient code seen to
give precise descriptions): `core/substructure_highlighter.py`,
`ui/prediction_page.py`, `ui/visualizer_page.py`, `ui/design_panel.py`,
`ui/substructure_page.py`, `ui/clipboard.py`,
`descriptors/descriptor_registry.py`, `descriptors/descriptor_explainer.py`,
`descriptors/extreme_finder.py`, `fingerprints/ecfp_interpreter.py`,
`fingerprints/maccs_interpreter.py`. Sections where information is incomplete
or ambiguous: (a) Python version — not specified in `requirements.txt`;
(b) scikit-learn version — not listed in `requirements.txt` despite being a
core dependency; (c) the precise system prompt text in
`llm/prompt_templates.py` — file not read; (d) details of how the training
CSV is loaded and column names are captured in `ui/sidebar.py` (only the
first 120 lines were read).*
