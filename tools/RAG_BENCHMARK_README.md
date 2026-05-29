# RAG benchmark

Use `rag_benchmark.py` to run the same question set against the RAGMODEX chat API
with RAG enabled and disabled.

## Generate the annotated set

The generator reads the saved RAGMODEX session under `data/session/` and writes
ground-truth answers computed from the actual loaded model, dataset, SHAP
explainer, bit database and applicability-domain pipeline.

```powershell
venv\Scripts\python.exe tools\generate_rag_benchmark_set.py
```

Generated files:

- `benchmark_inputs/questions.txt`
- `benchmark_inputs/questions_annotated.csv`
- `benchmark_inputs/questions_annotated.json`
- `benchmark_inputs/rag_reference_corpus.txt`

For conceptual retrieval precision@5, index `README.md`, `ARCHITECTURE.md`,
`GLUT-1 data/README.md`, or the compact
`benchmark_inputs/rag_reference_corpus.txt` into the RAG corpus before running
the benchmark.

```powershell
python tools\index_rag_corpus.py benchmark_inputs\rag_reference_corpus.txt
```

For the broader project documentation:

```powershell
python tools\index_rag_corpus.py README.md ARCHITECTURE.md "GLUT-1 data\README.md"
```

## Input

Create a UTF-8 `.txt` file with one question per line, or use the generated
`benchmark_inputs/questions.txt`:

```text
What is ECFP?
Predict CCCCC and explain the main SHAP bits.
What is the IC50 of this compound?
```

Blank lines and lines starting with `#` are ignored. You can optionally add an
ID with a tab:

```text
concept_001	What is ECFP?
edge_001	Predict not-a-smiles.
```

## Run

Start RAGMODEX first, then run:

```powershell
python tools\rag_benchmark.py benchmark_inputs\questions.txt --provider groq --models llama-3.3-70b-versatile llama-3.1-8b-instant qwen/qwen3-32b
```

For a single model:

```powershell
python tools\rag_benchmark.py benchmark_inputs\questions.txt --provider groq --models llama-3.3-70b-versatile
```

Only RAG-on:

```powershell
python tools\rag_benchmark.py benchmark_inputs\questions.txt --conditions rag-on
```

Only RAG-off:

```powershell
python tools\rag_benchmark.py benchmark_inputs\questions.txt --conditions rag-off
```

If the API key is not already configured in Settings or `.env`, pass it for the
current run:

```powershell
python tools\rag_benchmark.py questions.txt --provider groq --api-key YOUR_KEY
```

## Outputs

The script writes files under `benchmark_outputs/`:

- `.jsonl`: full machine-readable records, including retrieved chunks for RAG-on.
- `.csv`: compact table with manual annotation columns.
- `.md`: human-readable report with every question and answer.

The CSV includes empty columns for manual scoring:

- `manual_category`
- `expected_answer`
- `required_chunks_or_data`
- `pass_fail`
- `annotator_notes`

Suggested categories: `molecular`, `conceptual`, `edge_case`,
`hallucination_probe`.
